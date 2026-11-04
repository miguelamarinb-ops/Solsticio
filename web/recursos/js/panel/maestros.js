// Categorías del catálogo y sedes de la tienda (administración).
import { el, sinPrefijo } from "../comun.js";
import { aviso, campo, encabezado, errorEn, papi, tabla } from "./ui.js";

function formulario(titulo, campos, textoBoton, enviar) {
  const zonaError = el("div");
  const form = el("form", { class: "tarjeta", novalidate: true },
    el("h2", {}, titulo), el("div", { class: "campos" }, campos), zonaError,
    el("button", { class: "boton", type: "submit" }, textoBoton));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    zonaError.replaceChildren();
    const datos = Object.fromEntries([...new FormData(form)].map(([k, v]) => [k, v.trim()]).filter(([, v]) => v));
    try { await enviar(datos); form.reset(); } catch (error) { errorEn(zonaError, error); }
  });
  return form;
}

export async function render(principal, ctx) {
  const [categorias, sedes] = await Promise.all([papi("/categorias"), papi("/sedes")]);

  const formCategoria = formulario("Nueva categoría", [
    campo("Nombre", el("input", { name: "nombre", maxlength: 60, required: true })),
    campo("Descripción", el("input", { name: "descripcion", maxlength: 200 })),
  ], "Crear categoría", async (datos) => {
    if (!datos.nombre) throw new Error("Escribe el nombre.");
    await papi("/categorias", { metodo: "POST", cuerpo: datos });
    aviso("Categoría creada.");
    render(principal, ctx);
  });

  const formSede = formulario("Nueva sede", [
    campo("Nombre", el("input", { name: "nombre", maxlength: 80, required: true, placeholder: "Solsticio Usaquén" })),
    campo("Dirección", el("input", { name: "direccion", maxlength: 150, required: true })),
    campo("Ciudad", el("input", { name: "ciudad", maxlength: 60, value: "Bogotá" })),
    campo("Teléfono", el("input", { name: "telefono", maxlength: 20, type: "tel" })),
  ], "Crear sede", async (datos) => {
    if (!datos.nombre || !datos.direccion) throw new Error("Escribe el nombre y la dirección.");
    await papi("/sedes", { metodo: "POST", cuerpo: datos });
    aviso("Sede creada. Ya aparece en la tienda.");
    ctx.sedes = await papi("/sedes");
    render(principal, ctx);
  });

  principal.replaceChildren(
    encabezado("Categorías y sedes", "Cómo se agrupa el catálogo y dónde se vende."),
    el("div", { class: "rejilla-panel rejilla-panel--detalle" },
      el("section", { class: "tarjeta" }, el("h2", {}, "Categorías"),
        tabla([{ titulo: "Nombre", valor: (c) => el("strong", {}, c.nombre) }, { titulo: "Descripción", valor: (c) => c.descripcion || "" }], categorias)),
      formCategoria),
    el("div", { class: "rejilla-panel rejilla-panel--detalle" },
      el("section", { class: "tarjeta" }, el("h2", {}, "Sedes"),
        tabla([
          { titulo: "Sede", valor: (s) => el("strong", {}, sinPrefijo(s.nombre)) },
          { titulo: "Dirección", valor: (s) => `${s.direccion}, ${s.ciudad}` },
          { titulo: "Teléfono", valor: (s) => s.telefono || "" },
        ], sedes)),
      formSede));
}
