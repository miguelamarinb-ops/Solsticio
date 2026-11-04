// Lista de pedidos con filtros y búsqueda por el código QR del pedido.
import { el, fechaHora, precio, sinPrefijo } from "../comun.js";
import {
  campo, encabezado, errorEn, insignia, opcionesSedes, paginacion, papi, selector, tabla,
} from "./ui.js";

const ESTADOS = ["PENDIENTE", "PAGADO", "PREPARANDO", "ENVIADO", "ENTREGADO", "CANCELADO"];

export async function render(principal, ctx) {
  const q = ctx.consulta();
  const filtros = { estado: q.get("estado") || "", canal: q.get("canal") || "", id_sede: q.get("id_sede") || "", page: Number(q.get("page")) || 1 };
  const zona = el("div");
  const zonaBusqueda = el("div");

  function aplicar(cambios) {
    Object.assign(filtros, cambios);
    const p = new URLSearchParams(Object.entries(filtros).filter(([k, v]) => v && !(k === "page" && v === 1)));
    history.replaceState(null, "", `#/pedidos${p.toString() ? `?${p}` : ""}`);
    cargar();
  }

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Cargando pedidos…"));
    const p = new URLSearchParams({ page: filtros.page, size: 20 });
    for (const k of ["estado", "canal", "id_sede"]) if (filtros[k]) p.set(k, filtros[k]);
    const datos = await papi(`/pedidos?${p}`);
    zona.replaceChildren(
      tabla([
        { titulo: "Código", valor: (x) => el("a", { href: `#/pedidos/${x.id_pedido}` }, x.codigo_qr) },
        { titulo: "Fecha", valor: (x) => fechaHora(x.fecha_pedido) },
        { titulo: "Canal", valor: (x) => insignia(x.canal) },
        { titulo: "Cliente", valor: (x) => (x.cliente ? `${x.cliente.nombres} ${x.cliente.apellidos || ""}` : "Sin identificar") },
        { titulo: "Sede", valor: (x) => sinPrefijo(x.sede.nombre) },
        { titulo: "Total", valor: (x) => precio(x.total), clase: "num" },
        { titulo: "Estado", valor: (x) => insignia(x.estado) },
      ], datos.items, { vacio: "No hay pedidos con estos filtros.", alClic: (x) => ctx.navegar(`#/pedidos/${x.id_pedido}`) }),
      paginacion({ pagina: datos.page, total: datos.total, tamano: datos.size, alCambiar: (n) => aplicar({ page: n }) }));
  }

  const busqueda = el("form", { class: "busqueda-codigo", role: "search" },
    el("label", { for: "buscar-pedido", class: "solo-lector" }, "Código del pedido"),
    el("input", { id: "buscar-pedido", name: "codigo", placeholder: "SOL-P-00000001", autocomplete: "off" }),
    el("button", { class: "boton boton--secundario", type: "submit" }, "Buscar pedido"));
  busqueda.addEventListener("submit", async (e) => {
    e.preventDefault();
    const codigo = busqueda.codigo.value.trim().toUpperCase();
    if (!codigo) return;
    try {
      const pedido = await papi(`/pedidos/qr/${encodeURIComponent(codigo)}`);
      ctx.navegar(`#/pedidos/${pedido.id_pedido}`);
    } catch (error) {
      errorEn(zonaBusqueda, error.estado === 404 ? new Error(`No existe un pedido con el código ${codigo}.`) : error);
    }
  });

  const barra = el("div", { class: "filtros-barra" },
    campo("Estado", selector("estado", [["", "Todos"], ...ESTADOS.map((e) => [e, insignia(e).textContent])], filtros.estado,
      { onchange: (e) => aplicar({ estado: e.target.value, page: 1 }) })),
    campo("Canal", selector("canal", [["", "Todos"], ["WEB", "Web"], ["TIENDA", "Tienda"]], filtros.canal,
      { onchange: (e) => aplicar({ canal: e.target.value, page: 1 }) })),
    ctx.esAdmin ? campo("Sede", selector("id_sede", opcionesSedes(ctx.sedes, "Todas"), filtros.id_sede,
      { onchange: (e) => aplicar({ id_sede: e.target.value, page: 1 }) })) : null,
    busqueda);

  principal.replaceChildren(
    encabezado("Pedidos", ctx.esAdmin ? "Ventas web y en tienda de todas las sedes." : `Ventas de ${sinPrefijo(ctx.usuario.sede?.nombre)}.`,
      el("a", { class: "boton", href: "#/mostrador" }, "Nueva venta")),
    barra, zonaBusqueda, zona);
  await cargar();
}
