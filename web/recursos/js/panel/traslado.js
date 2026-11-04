// Detalle de un traslado: la sede de origen lo despacha y la de destino lo recibe.
// Cada paso genera su movimiento de inventario (salida y entrada).
import { el, fechaHora, sinPrefijo } from "../comun.js";
import { aviso, confirmar, datos, encabezado, errorEn, insignia, papi, tabla } from "./ui.js";

export async function render(principal, ctx, { id }) {
  const t = await papi(`/traslados/${id}`);
  const zonaError = el("div");
  const miSede = ctx.usuario.sede?.id_sede;
  const puedeDespachar = t.estado === "SOLICITADO" && (ctx.esAdmin || miSede === t.sede_origen.id_sede);
  const puedeRecibir = t.estado === "EN_TRANSITO" && (ctx.esAdmin || miSede === t.sede_destino.id_sede);

  async function accion(paso, texto) {
    const ok = await confirmar(texto, paso === "despachar"
      ? `Se descontarán ${t.items.reduce((s, i) => s + i.cantidad, 0)} unidades de ${sinPrefijo(t.sede_origen.nombre)}.`
      : `Se sumarán las unidades a ${sinPrefijo(t.sede_destino.nombre)}.`, { accion: texto });
    if (!ok) return;
    try {
      await papi(`/traslados/${t.id_traslado}/${paso}`, { metodo: "PATCH" });
      aviso(paso === "despachar" ? "Traslado despachado." : "Traslado recibido.");
      render(principal, ctx, { id });
    } catch (error) { errorEn(zonaError, error); }
  }

  principal.replaceChildren(
    el("p", { class: "migas" }, el("a", { href: "#/traslados" }, "Traslados"), ` / #${t.id_traslado}`),
    encabezado(`Traslado #${t.id_traslado}`, `${sinPrefijo(t.sede_origen.nombre)} hacia ${sinPrefijo(t.sede_destino.nombre)}`),
    el("div", { class: "estado-pedido" }, insignia(t.estado)),
    el("ol", { class: "pasos", "aria-label": "Avance del traslado" },
      ["SOLICITADO", "EN_TRANSITO", "RECIBIDO"].map((estado, i, lista) => {
        const indice = lista.indexOf(t.estado);
        return el("li", { class: i < indice ? "hecho" : i === indice ? "actual" : null, "aria-current": i === indice ? "step" : null },
          insignia(estado).textContent);
      })),
    el("div", { class: "pagina__acciones pagina__acciones--bloque" },
      puedeDespachar ? el("button", { class: "boton", type: "button", onclick: () => accion("despachar", "Despachar") }, "Despachar") : null,
      puedeRecibir ? el("button", { class: "boton", type: "button", onclick: () => accion("recibir", "Confirmar recepción") }, "Confirmar recepción") : null),
    zonaError,
    el("div", { class: "rejilla-panel rejilla-panel--detalle" },
      el("section", { class: "tarjeta" },
        el("h2", {}, "Prendas"),
        tabla([
          { titulo: "Prenda", valor: (i) => i.descripcion },
          { titulo: "SKU", valor: (i) => el("small", {}, i.sku) },
          { titulo: "Unidades", valor: (i) => String(i.cantidad), clase: "num" },
        ], t.items)),
      el("section", { class: "tarjeta" },
        el("h2", {}, "Datos"),
        datos([["Solicitado por", t.solicitado_por], ["Fecha de solicitud", fechaHora(t.fecha_solicitud)],
          ["Recibido por", t.recibido_por], ["Fecha de recepción", fechaHora(t.fecha_recepcion)]]))),
  );
}
