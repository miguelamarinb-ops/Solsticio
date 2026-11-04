// Ficha técnica (MongoDB) dibujada como la etiqueta cosida de una prenda.
// La usan el detalle de la tienda y el editor de fichas del panel (vista previa).
import { el } from "./comun.js";

const NOMBRES_ATRIBUTO = {
  material: "Material", gramaje_gsm: "Gramaje", cuello: "Cuello", manga: "Manga", fit: "Corte",
  tiro: "Tiro", elasticidad: "Elasticidad", lavado: "Lavado", bolsillos: "Bolsillos", cierre: "Cierre",
  certificaciones: "Certificaciones", columna_agua_mm: "Columna de agua", peso_denim: "Peso del denim",
  calidad_tela: "Calidad de la tela", igual_a_la_foto: "Igual a la foto",
};

export function nombreAtributo(clave) {
  if (NOMBRES_ATRIBUTO[clave]) return NOMBRES_ATRIBUTO[clave];
  const texto = clave.replaceAll("_", " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export function valorAtributo(clave, valor) {
  if (clave === "gramaje_gsm") return `${valor} g/m²`;
  if (clave === "columna_agua_mm") return `${Number(valor).toLocaleString("es-CO")} mm`;
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  if (Array.isArray(valor)) return valor.map((v) => (typeof v === "object" ? Object.values(v).join(" ") : v)).join(", ");
  if (valor && typeof valor === "object") return Object.values(valor).join(", ");
  return String(valor);
}

export function etiqueta(ficha, { id = "titulo-etiqueta" } = {}) {
  const { composicion, pais_origen: origen, ...resto } = ficha.atributos || {};
  const lineas = Array.isArray(composicion) && composicion.length
    ? composicion.map((c) => `${c.porcentaje}% ${c.fibra}`)
    : resto.material ? [resto.material] : [];
  if (lineas.length) delete resto.material;   // ya se lee en la composición

  return el("aside", { class: "etiqueta", "aria-labelledby": id },
    el("h2", { id }, "SOLSTICIO", el("span", { class: "solo-lector" }, ": ficha técnica")),
    lineas.length ? el("p", { class: "etiqueta__composicion" }, lineas.flatMap((l, i) => (i ? [el("br"), l] : [l]))) : null,
    Object.keys(resto).length
      ? el("dl", {}, Object.entries(resto).flatMap(([clave, valor]) => [
        el("dt", {}, nombreAtributo(clave)), el("dd", {}, valorAtributo(clave, valor))]))
      : null,
    ficha.cuidados?.length ? el("ul", { "aria-label": "Cuidados" }, ficha.cuidados.map((c) => el("li", {}, c))) : null,
    origen ? el("p", { class: "etiqueta__origen" }, `Hecho en ${origen}`) : null,
  );
}
