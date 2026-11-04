// Moderación de opiniones (MongoDB): responder como tienda, ocultar o publicar,
// y eliminar. El nombre de cada prenda se trae de MySQL.
import { el, estrellas, fechaHora } from "../comun.js";
import { aviso, campo, confirmar, encabezado, errorEn, insignia, paginacion, papi, selector } from "./ui.js";
import { nombreAtributo } from "../etiqueta.js";

const AJUSTES = { PEQUENA: "le quedó pequeña", EXACTA: "talla exacta", GRANDE: "le quedó grande" };

export async function render(principal, ctx) {
  const filtros = { estado: "", calificacion: "", page: 1 };
  const zona = el("div");

  function tarjeta(r) {
    const zonaError = el("div");
    const respuesta = el("textarea", { rows: 2, maxlength: 1000, placeholder: "Escribe la respuesta de Solsticio" });

    async function moderar(cuerpo, mensaje) {
      try {
        await papi(`/resenas/${r.id}`, { metodo: "PATCH", cuerpo });
        aviso(mensaje);
        cargar();
      } catch (error) { errorEn(zonaError, error); }
    }

    return el("article", { class: `tarjeta opinion${r.estado === "OCULTA" ? " opinion--oculta" : ""}` },
      el("div", { class: "opinion__cabeza" },
        el("a", { href: `#/productos/${r.id_producto}` }, r.producto || `Prenda ${r.id_producto}`),
        insignia(r.estado),
        r.compra_verificada ? insignia("Compra verificada", "verde") : null),
      el("div", { class: "opinion__cabeza" }, estrellas(r.calificacion), r.titulo ? el("strong", {}, r.titulo) : null),
      el("p", {}, r.comentario),
      el("p", { class: "nota" }, [
        `${r.autor.nombre} (${r.autor.email})`, fechaHora(r.fecha),
        r.talla ? `compró talla ${r.talla} ${r.color}` : null,
        r.ajuste_talla ? AJUSTES[r.ajuste_talla] : null,
        r.util ? `${r.util} ${r.util === 1 ? "persona la marcó útil" : "personas la marcaron útil"}` : null,
      ].filter(Boolean).join(", ")),
      r.atributos ? el("p", { class: "nota" }, Object.entries(r.atributos).map(([k, v]) => `${nombreAtributo(k)}: ${typeof v === "boolean" ? (v ? "sí" : "no") : v}`).join("; ")) : null,
      (r.respuestas || []).map((resp) => el("div", { class: "respuesta-tienda" },
        el("strong", {}, `${resp.nombre}, ${fechaHora(resp.fecha)}`), resp.texto)),
      el("details", { class: "plegable" }, el("summary", {}, "Responder"),
        campo("Respuesta", respuesta),
        el("button", { class: "boton boton--chico", type: "button", onclick: () => {
          if (!respuesta.value.trim()) return;
          moderar({ respuesta: respuesta.value.trim() }, "Respuesta publicada.");
        } }, "Publicar respuesta")),
      zonaError,
      el("div", { class: "fila-botones" },
        r.estado === "PUBLICADA"
          ? el("button", { class: "boton boton--secundario boton--chico", type: "button", onclick: () => moderar({ estado: "OCULTA" }, "Opinión oculta en la tienda.") }, "Ocultar")
          : el("button", { class: "boton boton--secundario boton--chico", type: "button", onclick: () => moderar({ estado: "PUBLICADA" }, "Opinión publicada.") }, "Publicar"),
        el("button", { class: "boton boton--peligro-texto boton--chico", type: "button", onclick: async () => {
          if (!await confirmar("Eliminar opinión", "Se borra para siempre. Si solo quieres que no se vea, ocúltala.", { accion: "Eliminar", peligro: true })) return;
          try { await papi(`/resenas/${r.id}`, { metodo: "DELETE" }); aviso("Opinión eliminada."); cargar(); } catch (error) { errorEn(zonaError, error); }
        } }, "Eliminar")));
  }

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Cargando opiniones…"));
    const p = new URLSearchParams({ page: filtros.page, size: 10 });
    if (filtros.estado) p.set("estado", filtros.estado);
    if (filtros.calificacion) p.set("calificacion", filtros.calificacion);
    const datos = await papi(`/resenas?${p}`);
    zona.replaceChildren(
      datos.items.length ? el("div", { class: "pila" }, datos.items.map(tarjeta)) : el("div", { class: "vacio" }, el("p", {}, "No hay opiniones con estos filtros.")),
      paginacion({ pagina: datos.page, total: datos.total, tamano: datos.size, alCambiar: (n) => { filtros.page = n; cargar(); } }));
  }

  const cambio = (k) => (e) => { filtros[k] = e.target.value; filtros.page = 1; cargar(); };
  principal.replaceChildren(
    encabezado("Opiniones", "Lo que dicen los clientes de cada prenda. Se guardan en MongoDB."),
    el("div", { class: "filtros-barra" },
      campo("Estado", selector("estado", [["", "Todas"], ["PUBLICADA", "Publicadas"], ["OCULTA", "Ocultas"]], "", { onchange: cambio("estado") })),
      campo("Calificación", selector("calificacion", [["", "Todas"], ...[5, 4, 3, 2, 1].map((n) => [n, `${n} estrellas`])], "", { onchange: cambio("calificacion") }))),
    zona);
  await cargar();
}
