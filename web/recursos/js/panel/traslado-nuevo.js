// Crear traslado (administración): origen, destino y prendas. La API valida que
// el origen tenga existencias y, si no, dice en qué otras sedes hay.
import { el, sinPrefijo } from "../comun.js";
import { aviso, buscadorVariantes, campo, encabezado, errorEn, opcionesSedes, papi, selector } from "./ui.js";

export async function render(principal, ctx) {
  let origen = ctx.sedes[0]?.id_sede;
  let destino = ctx.sedes[1]?.id_sede ?? origen;
  let lineas = [];
  const zonaLineas = el("div");
  const zonaError = el("div");

  function pintar() {
    if (!lineas.length) { zonaLineas.replaceChildren(el("p", { class: "vacio" }, "Agrega las prendas que se van a mover.")); return; }
    zonaLineas.replaceChildren(el("ul", { class: "venta" }, lineas.map((l) => {
      const cantidad = el("input", { type: "number", min: 1, value: l.cantidad, "aria-label": `Unidades de ${l.descripcion}` });
      cantidad.addEventListener("change", () => { l.cantidad = Math.max(1, Number(cantidad.value) || 1); });
      return el("li", {},
        el("div", {}, el("strong", {}, l.descripcion), el("span", { class: "nota" }, l.sku)),
        cantidad,
        el("button", { class: "linea__quitar", type: "button", onclick: () => { lineas = lineas.filter((x) => x !== l); pintar(); } }, "Quitar"));
    })));
  }

  const form = el("form", { class: "tarjeta", novalidate: true },
    el("h2", {}, "Traslado"),
    el("div", { class: "campos" },
      campo("Sale de", selector("origen", opcionesSedes(ctx.sedes), origen, { onchange: (e) => { origen = Number(e.target.value); } })),
      campo("Llega a", selector("destino", opcionesSedes(ctx.sedes), destino, { onchange: (e) => { destino = Number(e.target.value); } }))),
    zonaLineas,
    zonaError,
    el("button", { class: "boton", type: "submit" }, "Crear traslado"));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    zonaError.replaceChildren();
    if (origen === destino) { errorEn(zonaError, new Error("La sede de origen y la de destino deben ser distintas.")); return; }
    if (!lineas.length) { errorEn(zonaError, new Error("Agrega al menos una prenda.")); return; }
    try {
      const t = await papi("/traslados", {
        metodo: "POST",
        cuerpo: { id_sede_origen: origen, id_sede_destino: destino, items: lineas.map((l) => ({ id_variante: l.id_variante, cantidad: l.cantidad })) },
      });
      aviso(`Traslado #${t.id_traslado} creado. Falta que ${sinPrefijo(t.sede_origen.nombre)} lo despache.`);
      ctx.navegar(`#/traslados/${t.id_traslado}`);
    } catch (error) { errorEn(zonaError, error); }
  });

  principal.replaceChildren(
    el("p", { class: "migas" }, el("a", { href: "#/traslados" }, "Traslados"), " / Nuevo"),
    encabezado("Nuevo traslado", "La sede de origen lo despacha y la de destino confirma que llegó."),
    el("div", { class: "mostrador" },
      el("section", { class: "tarjeta" }, el("h2", {}, "Buscar prendas"),
        buscadorVariantes({
          sede: () => origen,
          alElegir: (v) => {
            if (!lineas.some((l) => l.id_variante === v.id_variante)) lineas.push({ ...v, cantidad: 1 });
            pintar();
          },
        })),
      form));
  pintar();
}
