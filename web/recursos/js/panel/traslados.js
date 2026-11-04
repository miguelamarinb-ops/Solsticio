// Lista de traslados entre sedes.
import { el, fechaHora, sinPrefijo } from "../comun.js";
import { campo, encabezado, insignia, paginacion, papi, selector, tabla } from "./ui.js";

export async function render(principal, ctx) {
  const filtros = { estado: ctx.consulta().get("estado") || "", page: 1 };
  const zona = el("div");

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Cargando traslados…"));
    const p = new URLSearchParams({ page: filtros.page, size: 20 });
    if (filtros.estado) p.set("estado", filtros.estado);
    const datos = await papi(`/traslados?${p}`);
    zona.replaceChildren(
      tabla([
        { titulo: "N.º", valor: (t) => el("a", { href: `#/traslados/${t.id_traslado}` }, `#${t.id_traslado}`) },
        { titulo: "Desde", valor: (t) => sinPrefijo(t.sede_origen.nombre) },
        { titulo: "Hacia", valor: (t) => sinPrefijo(t.sede_destino.nombre) },
        { titulo: "Unidades", valor: (t) => String(t.items.reduce((s, i) => s + i.cantidad, 0)), clase: "num" },
        { titulo: "Solicitado", valor: (t) => fechaHora(t.fecha_solicitud) },
        { titulo: "Estado", valor: (t) => insignia(t.estado) },
      ], datos.items, { vacio: "No hay traslados.", alClic: (t) => ctx.navegar(`#/traslados/${t.id_traslado}`) }),
      paginacion({ pagina: datos.page, total: datos.total, tamano: datos.size, alCambiar: (n) => { filtros.page = n; cargar(); } }));
  }

  principal.replaceChildren(
    encabezado("Traslados", ctx.esAdmin ? "Mercancía que se mueve entre sedes." : "Traslados que salen o llegan a tu sede.",
      ctx.esAdmin ? el("a", { class: "boton", href: "#/traslados/nuevo" }, "Nuevo traslado") : null),
    el("div", { class: "filtros-barra" },
      campo("Estado", selector("estado", [["", "Todos"], ["SOLICITADO", "Solicitado"], ["EN_TRANSITO", "En tránsito"], ["RECIBIDO", "Recibido"], ["CANCELADO", "Cancelado"]],
        filtros.estado, { onchange: (e) => { filtros.estado = e.target.value; filtros.page = 1; cargar(); } }))),
    zona);
  await cargar();
}
