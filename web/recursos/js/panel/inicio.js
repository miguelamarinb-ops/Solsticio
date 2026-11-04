// Inicio: lo que hay que atender hoy (pedidos por cobrar y por preparar,
// traslados en camino, existencias agotadas) y, para administración, la
// actividad reciente (MongoDB) y las prendas más escaneadas.
import { el, fechaHora, precio, sinPrefijo } from "../comun.js";
import { encabezado, insignia, legible, papi, tabla } from "./ui.js";

const total = (promesa) => promesa.then((r) => r.total).catch(() => null);

function cifra(valor, texto, href, tono) {
  return el("a", { class: `cifra${tono ? ` cifra--${tono}` : ""}`, href },
    el("strong", {}, valor == null ? "—" : String(valor)), el("span", {}, texto));
}

export async function render(principal, ctx) {
  const { usuario, esAdmin } = ctx;
  const sede = esAdmin ? "" : `&id_sede=${usuario.id_sede ?? usuario.sede?.id_sede ?? ""}`;

  const [porCobrar, porPreparar, enCamino, agotados, recientes] = await Promise.all([
    total(papi(`/pedidos?estado=PENDIENTE&size=1${sede}`)),
    total(papi(`/pedidos?estado=PAGADO&size=1${sede}`)),
    total(papi("/traslados?estado=EN_TRANSITO&size=1")),
    papi(`/stock?bajo_minimo=true${sede}`).catch(() => []),
    papi(`/pedidos?size=6${sede}`).catch(() => ({ items: [] })),
  ]);

  const saludo = new Date().getHours() < 12 ? "Buenos días" : new Date().getHours() < 19 ? "Buenas tardes" : "Buenas noches";
  principal.replaceChildren(
    encabezado(`${saludo}, ${usuario.nombres}`,
      esAdmin ? "Esto es lo que pide atención hoy en las sedes." : `Esto es lo que pide atención hoy en ${sinPrefijo(usuario.sede?.nombre)}.`,
      el("a", { class: "boton", href: "#/mostrador" }, "Nueva venta"),
      el("a", { class: "boton boton--secundario", href: "#/inventario/ingreso" }, "Registrar ingreso")),
    el("section", { class: "cifras", "aria-label": "Pendientes" },
      cifra(porCobrar, "pedidos por cobrar", "#/pedidos?estado=PENDIENTE", porCobrar ? "sol" : null),
      cifra(porPreparar, "pagados por preparar o entregar", "#/pedidos?estado=PAGADO", porPreparar ? "azul" : null),
      cifra(enCamino, "traslados en camino", "#/traslados?estado=EN_TRANSITO"),
      cifra(agotados.length, "referencias agotadas", "#/inventario?bajo_minimo=1", agotados.length ? "rojo" : null)),
    el("div", { class: "rejilla-panel" },
      el("section", { class: "tarjeta" },
        el("h2", {}, "Últimos pedidos"),
        tabla([
          { titulo: "Código", valor: (p) => el("a", { href: `#/pedidos/${p.id_pedido}` }, p.codigo_qr) },
          { titulo: "Canal", valor: (p) => insignia(p.canal) },
          { titulo: "Total", valor: (p) => precio(p.total), clase: "num" },
          { titulo: "Estado", valor: (p) => insignia(p.estado) },
        ], recientes.items, { vacio: "Todavía no hay pedidos." })),
      el("section", { class: "tarjeta" },
        el("h2", {}, "Por reponer"),
        tabla([
          { titulo: "Prenda", valor: (s) => s.descripcion },
          { titulo: "Sede", valor: (s) => sinPrefijo(s.sede) },
          { titulo: "Quedan", valor: (s) => String(s.cantidad), clase: "num" },
        ], agotados.slice(0, 6), { vacio: "Ninguna referencia está agotada." }),
        agotados.length > 6 ? el("p", { class: "nota" }, el("a", { href: "#/inventario?bajo_minimo=1" }, `Ver las ${agotados.length}`)) : null)),
  );

  if (esAdmin) {
    const [actividad, ranking] = await Promise.all([
      papi("/actividad?size=8").catch(() => ({ items: [] })),
      papi("/reportes/qr-mas-escaneados?dias=30&limite=5").catch(() => ({ items: [] })),
    ]);
    principal.append(el("div", { class: "rejilla-panel" },
      el("section", { class: "tarjeta" },
        el("h2", {}, "Actividad reciente del equipo"),
        el("p", { class: "nota" }, "Bitácora guardada en MongoDB."),
        tabla([
          { titulo: "Cuándo", valor: (a) => fechaHora(a.fecha) },
          { titulo: "Acción", valor: (a) => legible(a.accion.includes(".") ? a.accion.split(".")[1] : a.accion) },
          { titulo: "Resultado", valor: (a) => el("span", { class: a.exito ? "texto-si" : "texto-no" }, String(a.estado_http)) },
        ], actividad.items, { vacio: "Sin actividad registrada." }),
        el("p", { class: "nota" }, el("a", { href: "#/bitacora" }, "Ver la bitácora completa"))),
      el("section", { class: "tarjeta" },
        el("h2", {}, "Lo más escaneado en 30 días"),
        el("p", { class: "nota" }, "Escaneos (MongoDB) con stock al día (MySQL)."),
        tabla([
          { titulo: "Prenda", valor: (r) => r.descripcion },
          { titulo: "Escaneos", valor: (r) => String(r.escaneos.total), clase: "num" },
          { titulo: "Stock", valor: (r) => String(r.stock_total), clase: "num" },
        ], ranking.items, { vacio: "Aún no se han escaneado etiquetas." }),
        el("p", { class: "nota" }, el("a", { href: "#/reportes" }, "Ver el reporte")))));
  }
}
