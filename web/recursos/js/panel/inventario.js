// Inventario: existencias por sede, ingresos de mercancía, ajustes por conteo
// físico (administración) e historial de movimientos (administración).
import { el, fechaHora, sinPrefijo } from "../comun.js";
import {
  aviso, buscadorVariantes, campo, encabezado, errorEn, insignia, opcionesSedes, paginacion, papi,
  pestanas, selector, tabla,
} from "./ui.js";

const TIPOS = ["INGRESO", "VENTA", "DEVOLUCION", "TRASLADO_SALIDA", "TRASLADO_ENTRADA", "AJUSTE"];

export async function render(principal, ctx, { vista = "existencias" }) {
  const vistas = [["#/inventario", "Existencias"], ["#/inventario/ingreso", "Registrar ingreso"]];
  if (ctx.esAdmin) vistas.push(["#/inventario/ajuste", "Ajuste por conteo"], ["#/inventario/movimientos", "Movimientos"]);
  const actual = vista === "existencias" ? "#/inventario" : `#/inventario/${vista}`;
  if (!vistas.some(([href]) => href === actual)) throw Object.assign(new Error("Esta sección es solo para administración."), { estado: 403 });

  const contenido = el("div");
  principal.replaceChildren(
    encabezado("Inventario", "Cada cambio de existencias queda registrado como un movimiento."),
    pestanas(vistas, actual),
    contenido);
  const vistasRender = { existencias, ingreso, ajuste, movimientos };
  await vistasRender[vista](contenido, ctx);
}

// ---------------------------------------------------------------------
async function existencias(contenido, ctx) {
  const q = ctx.consulta();
  const filtros = { id_sede: q.get("id_sede") || "", bajo: q.get("bajo_minimo") === "1", texto: "" };
  const zona = el("div");
  let filas = [];

  const pintar = () => {
    const t = filtros.texto.toLowerCase();
    const visibles = t ? filas.filter((s) => `${s.descripcion} ${s.sku}`.toLowerCase().includes(t)) : filas;
    zona.replaceChildren(tabla([
      ...(ctx.esAdmin ? [{ titulo: "Sede", valor: (s) => sinPrefijo(s.sede) }] : []),
      { titulo: "Prenda", valor: (s) => s.descripcion },
      { titulo: "SKU", valor: (s) => el("small", {}, s.sku) },
      { titulo: "Existencias", valor: (s) => String(s.cantidad), clase: "num" },
      { titulo: "Reservadas", valor: (s) => String(s.cantidad_reservada), clase: "num" },
      { titulo: "Disponibles", valor: (s) => el("strong", { class: s.disponible > 0 ? "" : "texto-no" }, String(s.disponible)), clase: "num" },
      { titulo: "", valor: (s) => (s.bajo_minimo ? insignia("Agotada", "rojo") : "") },
    ], visibles, { vacio: "No hay existencias con estos filtros." }),
    el("p", { class: "nota" }, `${visibles.length} referencias. Reservadas = apartadas por pedidos web sin pagar.`));
  };

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Cargando existencias…"));
    const p = new URLSearchParams();
    if (filtros.id_sede) p.set("id_sede", filtros.id_sede);
    if (filtros.bajo) p.set("bajo_minimo", "true");
    filas = await papi(`/stock?${p}`);
    pintar();
  }

  const buscador = el("input", { type: "search", placeholder: "Filtrar por prenda o SKU" });
  buscador.addEventListener("input", () => { filtros.texto = buscador.value; pintar(); });
  const bajo = el("input", { type: "checkbox", checked: filtros.bajo });
  bajo.addEventListener("change", () => { filtros.bajo = bajo.checked; cargar(); });

  contenido.replaceChildren(
    el("div", { class: "filtros-barra" },
      ctx.esAdmin ? campo("Sede", selector("id_sede", opcionesSedes(ctx.sedes, "Todas"), filtros.id_sede,
        { onchange: (e) => { filtros.id_sede = e.target.value; cargar(); } })) : null,
      campo("Buscar", buscador),
      el("label", { class: "casilla" }, bajo, " Solo agotadas")),
    zona);
  await cargar();
}

// ---------------------------------------------------------------------
// Formulario con líneas de prendas (ingreso y ajuste comparten la estructura)
// ---------------------------------------------------------------------
function formularioLineas(ctx, { titulo, columnaCantidad, ayudaCantidad, observacionObligatoria, textoBoton, enviar, conExistencia }) {
  let idSede = ctx.esAdmin ? ctx.sedes[0]?.id_sede : ctx.usuario.sede?.id_sede;
  let lineas = [];
  const zonaLineas = el("div");
  const zonaError = el("div");
  const zonaResultado = el("div");

  async function agregar(v) {
    if (lineas.some((l) => l.id_variante === v.id_variante)) { aviso("Esa prenda ya está en la lista."); return; }
    const linea = { ...v, cantidad: conExistencia ? 0 : 1, actual: null };
    lineas.push(linea);
    if (conExistencia) {
      const filas = await papi(`/stock?id_sede=${idSede}&id_variante=${v.id_variante}`).catch(() => []);
      linea.actual = filas[0]?.cantidad ?? 0;
      linea.cantidad = linea.actual;
    }
    pintar();
  }

  function pintar() {
    if (!lineas.length) { zonaLineas.replaceChildren(el("p", { class: "vacio" }, "Agrega las prendas con el buscador.")); return; }
    zonaLineas.replaceChildren(el("ul", { class: "venta" }, lineas.map((l) => {
      const cantidad = el("input", { type: "number", min: conExistencia ? 0 : 1, value: l.cantidad, "aria-label": `${columnaCantidad} de ${l.descripcion}` });
      cantidad.addEventListener("change", () => { l.cantidad = Math.max(0, Number(cantidad.value) || 0); pintar(); });
      return el("li", {},
        el("div", {}, el("strong", {}, l.descripcion),
          el("span", { class: "nota" }, conExistencia ? `${l.sku}. En sistema: ${l.actual ?? "…"}${l.actual != null && l.cantidad !== l.actual ? `, diferencia ${l.cantidad - l.actual > 0 ? "+" : ""}${l.cantidad - l.actual}` : ""}` : l.sku)),
        cantidad,
        el("button", { class: "linea__quitar", type: "button", onclick: () => { lineas = lineas.filter((x) => x !== l); pintar(); } }, "Quitar"));
    })));
  }

  const observacion = el("input", { name: "observacion", maxlength: 200, required: observacionObligatoria });
  const form = el("form", { class: "tarjeta", novalidate: true },
    el("h2", {}, titulo),
    ctx.esAdmin
      ? campo("Sede", selector("id_sede", opcionesSedes(ctx.sedes), idSede, { onchange: (e) => { idSede = Number(e.target.value); lineas = []; pintar(); } }))
      : el("p", { class: "nota" }, `Sede: ${sinPrefijo(ctx.usuario.sede?.nombre)}`),
    zonaLineas,
    el("p", { class: "nota" }, ayudaCantidad),
    campo(observacionObligatoria ? "Motivo del ajuste" : "Observación (opcional)", observacion,
      observacionObligatoria ? "Por ejemplo: conteo físico de fin de mes." : "Por ejemplo, el número de la remisión del proveedor."),
    zonaError,
    el("button", { class: "boton", type: "submit" }, textoBoton));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    zonaError.replaceChildren();
    const validas = lineas.filter((l) => conExistencia || l.cantidad > 0);
    if (!validas.length) { errorEn(zonaError, new Error("Agrega al menos una prenda con cantidad.")); return; }
    if (observacionObligatoria && !observacion.value.trim()) { errorEn(zonaError, new Error("Escribe el motivo del ajuste.")); return; }
    try {
      const r = await enviar({ id_sede: idSede, observacion: observacion.value.trim() || undefined, lineas: validas });
      aviso(`${r.movimientos.length} movimientos registrados en ${sinPrefijo(r.sede)}.`);
      zonaResultado.replaceChildren(el("section", { class: "tarjeta" },
        el("h2", {}, "Resultado"),
        tabla([
          { titulo: "SKU", valor: (m) => m.sku },
          { titulo: "Movimiento", valor: (m) => insignia(m.tipo) },
          { titulo: "Cambio", valor: (m) => `${m.cantidad > 0 ? "+" : ""}${m.cantidad}`, clase: "num" },
          { titulo: "Antes", valor: (m) => String(m.stock_anterior), clase: "num" },
          { titulo: "Ahora", valor: (m) => el("strong", {}, String(m.stock_actual)), clase: "num" },
        ], r.movimientos, { vacio: "No hubo diferencias: las cantidades ya coincidían." })));
      lineas = [];
      form.reset();
      pintar();
    } catch (error) { errorEn(zonaError, error); }
  });

  pintar();
  return el("div", {},
    el("div", { class: "mostrador" },
      el("section", { class: "tarjeta" }, el("h2", {}, "Buscar prendas"), buscadorVariantes({ alElegir: agregar, sede: () => idSede })),
      form),
    zonaResultado);
}

async function ingreso(contenido, ctx) {
  contenido.replaceChildren(formularioLineas(ctx, {
    titulo: "Mercancía que llegó", columnaCantidad: "Unidades", textoBoton: "Registrar ingreso",
    ayudaCantidad: "Escribe cuántas unidades llegaron de cada prenda.",
    enviar: ({ id_sede, observacion, lineas }) => papi("/inventario/ingresos", {
      metodo: "POST", cuerpo: { id_sede, observacion, items: lineas.map((l) => ({ id_variante: l.id_variante, cantidad: l.cantidad })) },
    }),
  }));
}

async function ajuste(contenido, ctx) {
  contenido.replaceChildren(formularioLineas(ctx, {
    titulo: "Conteo físico", columnaCantidad: "Cantidad contada", textoBoton: "Aplicar ajuste",
    observacionObligatoria: true, conExistencia: true,
    ayudaCantidad: "Escribe cuántas unidades contaste en la bodega. El sistema registra solo la diferencia.",
    enviar: ({ id_sede, observacion, lineas }) => papi("/inventario/ajustes", {
      metodo: "POST", cuerpo: { id_sede, observacion, items: lineas.map((l) => ({ id_variante: l.id_variante, cantidad_contada: l.cantidad })) },
    }),
  }));
}

// ---------------------------------------------------------------------
async function movimientos(contenido, ctx) {
  const filtros = { id_sede: "", tipo: "", desde: "", hasta: "", page: 1 };
  const zona = el("div");

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Cargando movimientos…"));
    const p = new URLSearchParams({ page: filtros.page, size: 30 });
    for (const k of ["id_sede", "tipo", "desde", "hasta"]) if (filtros[k]) p.set(k, filtros[k]);
    const datos = await papi(`/inventario/movimientos?${p}`);
    zona.replaceChildren(
      tabla([
        { titulo: "Fecha", valor: (m) => fechaHora(m.fecha) },
        { titulo: "Tipo", valor: (m) => insignia(m.tipo) },
        { titulo: "Sede", valor: (m) => sinPrefijo(m.sede) },
        { titulo: "SKU", valor: (m) => m.sku },
        { titulo: "Cambio", valor: (m) => el("span", { class: m.cantidad > 0 ? "texto-si" : "texto-no" }, `${m.cantidad > 0 ? "+" : ""}${m.cantidad}`), clase: "num" },
        { titulo: "Origen", valor: (m) => (m.tipo_referencia ? `${m.tipo_referencia}${m.id_referencia ? ` #${m.id_referencia}` : ""}` : "") },
        { titulo: "Registró", valor: (m) => m.registrado_por || "Sistema" },
        { titulo: "Observación", valor: (m) => m.observacion || "" },
      ], datos.items, { vacio: "No hay movimientos con estos filtros." }),
      paginacion({ pagina: datos.page, total: datos.total, tamano: datos.size, alCambiar: (n) => { filtros.page = n; cargar(); } }));
  }

  const cambio = (clave) => (e) => { filtros[clave] = e.target.value; filtros.page = 1; cargar().catch((err) => errorEn(zona, err)); };
  contenido.replaceChildren(
    el("div", { class: "filtros-barra" },
      campo("Sede", selector("id_sede", opcionesSedes(ctx.sedes, "Todas"), "", { onchange: cambio("id_sede") })),
      campo("Tipo", selector("tipo", [["", "Todos"], ...TIPOS.map((t) => [t, insignia(t).textContent])], "", { onchange: cambio("tipo") })),
      campo("Desde", el("input", { type: "date", onchange: cambio("desde") })),
      campo("Hasta", el("input", { type: "date", onchange: cambio("hasta") }))),
    zona);
  await cargar();
}
