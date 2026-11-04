// Una prenda (administración): datos (MySQL), variantes talla × color (MySQL),
// ficha técnica con atributos libres (MongoDB) y etiquetas QR para imprimir.
import { el, foto, precio, qr } from "../comun.js";
import { etiqueta } from "../etiqueta.js";
import {
  aviso, campo, confirmar, encabezado, errorEn, papi, pestanas, selector, tabla,
} from "./ui.js";

const GENEROS = [["UNISEX", "Unisex"], ["MUJER", "Mujer"], ["HOMBRE", "Hombre"], ["INFANTIL", "Niños"]];
const ILUSTRACIONES = [
  "camiseta-oversize", "camiseta-cuello-v", "camiseta-manga-larga", "camiseta-infantil", "buzo-capota",
  "buzo-cuello-redondo", "chaqueta-jean", "chaqueta-impermeable", "jean-slim", "jean-recto", "vestido-midi", "gorra",
];

export async function render(principal, ctx, { id, vista = "datos" }) {
  const categorias = await papi("/categorias");
  if (!id) {
    principal.replaceChildren(
      el("p", { class: "migas" }, el("a", { href: "#/productos" }, "Prendas"), " / Nueva"),
      encabezado("Nueva prenda", "Después de guardarla podrás crear sus tallas y colores."),
      formularioDatos(ctx, categorias, null));
    return;
  }
  const producto = await papi(`/productos/${id}`);
  const base = `#/productos/${id}`;
  const contenido = el("div");
  principal.replaceChildren(
    el("p", { class: "migas" }, el("a", { href: "#/productos" }, "Prendas"), ` / ${producto.nombre}`),
    encabezado(producto.nombre, `${producto.categoria.nombre}, ${precio(producto.precio_base)}`,
      producto.activo ? el("a", { class: "boton boton--secundario", href: `/producto?id=${id}`, target: "_blank", rel: "noopener" }, "Ver en la tienda") : null),
    producto.activo ? "" : el("div", { class: "aviso" }, el("p", {}, "Esta prenda está desactivada: no aparece en la tienda ni se puede vender.")),
    pestanas([[base, "Datos"], [`${base}/variantes`, "Tallas y colores"], [`${base}/ficha`, "Ficha técnica"], [`${base}/etiquetas`, "Etiquetas QR"]],
      vista === "datos" ? base : `${base}/${vista}`),
    contenido);
  const vistas = { datos: () => formularioDatos(ctx, categorias, producto), variantes, ficha, etiquetas };
  if (!vistas[vista]) throw Object.assign(new Error("Esa sección no existe."), { estado: 404 });
  const nodo = await vistas[vista](producto, ctx);
  contenido.replaceChildren(nodo);
}

// ---------------------------------------------------------------------
// Datos básicos
// ---------------------------------------------------------------------
function formularioDatos(ctx, categorias, producto) {
  const zonaError = el("div");
  const imagenActual = producto ? (producto.imagenes.find((i) => i.es_principal) || producto.imagenes[0])?.url : null;
  const vista = el("div", { class: "vista-imagen" }, foto(imagenActual, producto?.nombre || "Prenda", { lazy: false }));
  const ilustracion = selector("ilustracion", [["", "Sin imagen"], ...ILUSTRACIONES.map((n) => [`/recursos/img/prendas/${n}.svg`, n.replaceAll("-", " ")])], "");
  ilustracion.addEventListener("change", () => vista.replaceChildren(foto(ilustracion.value, "Prenda", { lazy: false })));

  const form = el("form", { class: "tarjeta formulario-producto", novalidate: true },
    el("div", { class: "campos" },
      campo("Nombre", el("input", { name: "nombre", maxlength: 120, required: true, value: producto?.nombre || "" }), null, { ancho: true }),
      campo("Categoría", selector("id_categoria", categorias.map((c) => [c.id_categoria, c.nombre]), producto?.categoria.id_categoria)),
      campo("Para", selector("genero", GENEROS, producto?.genero || "UNISEX")),
      campo("Precio base (IVA incluido)", el("input", { name: "precio_base", type: "number", min: 1, step: 100, required: true, value: producto ? Number(producto.precio_base) : "" }),
        "Cada talla o color puede sumar un valor adicional."),
      campo("Descripción", el("textarea", { name: "descripcion", maxlength: 5000, rows: 4 }, producto?.descripcion || ""), null, { ancho: true }),
      producto ? null : campo("Imagen", ilustracion, "Ilustración de muestra. Las fotos reales se cargan como URL desde la API.")),
    producto ? null : vista,
    zonaError,
    el("div", { class: "fila-botones" },
      el("button", { class: "boton", type: "submit" }, producto ? "Guardar cambios" : "Crear prenda"),
      producto?.activo ? el("button", { class: "boton boton--peligro-texto", type: "button", onclick: desactivar }, "Desactivar prenda") : null,
      producto && !producto.activo ? el("button", { class: "boton boton--secundario", type: "button", onclick: () => guardar(true) }, "Reactivar prenda") : null));

  function leer() {
    const f = Object.fromEntries(new FormData(form));
    return {
      nombre: f.nombre?.trim(), id_categoria: Number(f.id_categoria), genero: f.genero,
      precio_base: Number(f.precio_base), descripcion: f.descripcion?.trim() || null,
    };
  }

  async function guardar(reactivar = false) {
    zonaError.replaceChildren();
    const datos = leer();
    if (!datos.nombre || !datos.precio_base) { errorEn(zonaError, new Error("Escribe el nombre y el precio.")); return; }
    try {
      if (producto) {
        await papi(`/productos/${producto.id_producto}`, { metodo: "PUT", cuerpo: reactivar ? { ...datos, activo: true } : datos });
        aviso(reactivar ? "Prenda reactivada." : "Cambios guardados.");
        ctx.refrescar();
      } else {
        const imagen = form.ilustracion.value;
        const nuevo = await papi("/productos", {
          metodo: "POST", cuerpo: { ...datos, imagenes: imagen ? [{ url: imagen, orden: 1, es_principal: true }] : [] },
        });
        aviso("Prenda creada. Ahora agrega sus tallas y colores.");
        ctx.navegar(`#/productos/${nuevo.id_producto}/variantes`);
      }
    } catch (error) { errorEn(zonaError, error); }
  }

  async function desactivar() {
    const ok = await confirmar("Desactivar prenda", "Dejará de verse en la tienda y no se podrá vender. Su historial de ventas se conserva.", { accion: "Desactivar", peligro: true });
    if (!ok) return;
    try {
      await papi(`/productos/${producto.id_producto}`, { metodo: "DELETE" });
      aviso("Prenda desactivada.");
      ctx.refrescar();
    } catch (error) { errorEn(zonaError, error); }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); guardar(); });
  return form;
}

// ---------------------------------------------------------------------
// Variantes
// ---------------------------------------------------------------------
async function variantes(producto, ctx) {
  const [tallas, colores] = await Promise.all([papi("/tallas"), papi("/colores")]);
  const zonaError = el("div");

  const form = el("form", { class: "tarjeta", novalidate: true },
    el("h2", {}, "Agregar tallas y colores"),
    el("p", { class: "nota" }, "Se crea una variante por cada combinación, con su SKU y su código QR."),
    el("fieldset", { class: "opciones" }, el("legend", {}, "Tallas"),
      el("div", { class: "opciones__lista" }, tallas.map((t) => el("label", { class: "opcion" },
        el("input", { type: "checkbox", name: "talla", value: t.id_talla }), el("span", {}, t.valor))))),
    el("fieldset", { class: "opciones" }, el("legend", {}, "Colores"),
      el("div", { class: "opciones__lista" }, colores.map((c) => el("label", { class: "opcion" },
        el("input", { type: "checkbox", name: "color", value: c.id_color }),
        el("span", {}, el("span", { class: "muestra-color", style: `background:${c.codigo_hex}`, "aria-hidden": "true" }), c.nombre))))),
    campo("Valor adicional por variante", el("input", { name: "precio_adicional", type: "number", min: 0, step: 100, value: 0 }),
      "Por ejemplo, las tallas grandes pueden costar un poco más."),
    zonaError,
    el("button", { class: "boton", type: "submit" }, "Crear variantes"));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    zonaError.replaceChildren();
    const f = new FormData(form);
    const ts = f.getAll("talla").map(Number);
    const cs = f.getAll("color").map(Number);
    if (!ts.length || !cs.length) { errorEn(zonaError, new Error("Elige al menos una talla y un color.")); return; }
    const adicional = Number(f.get("precio_adicional")) || 0;
    try {
      const r = await papi(`/productos/${producto.id_producto}/variantes`, {
        metodo: "POST", cuerpo: { combinaciones: ts.flatMap((t) => cs.map((c) => ({ id_talla: t, id_color: c, precio_adicional: adicional }))) },
      });
      aviso(`${r.creadas.length} variantes creadas${r.omitidas.length ? `; ${r.omitidas.length} ya existían` : ""}.`);
      ctx.refrescar();
    } catch (error) { errorEn(zonaError, error.estado === 409 ? new Error("Todas esas combinaciones ya existen.") : error); }
  });

  return el("div", { class: "rejilla-panel rejilla-panel--detalle" },
    el("section", { class: "tarjeta" },
      el("h2", {}, `Variantes (${producto.variantes.length})`),
      tabla([
        { titulo: "Talla", valor: (v) => el("strong", {}, v.talla) },
        { titulo: "Color", valor: (v) => el("span", { class: "con-muestra" }, el("span", { class: "muestra-color", style: `background:${v.color.codigo_hex}` }), v.color.nombre) },
        { titulo: "SKU", valor: (v) => el("small", {}, v.sku) },
        { titulo: "QR", valor: (v) => el("small", {}, v.codigo_qr) },
        { titulo: "Precio", valor: (v) => precio(v.precio_final), clase: "num" },
        { titulo: "Existencias", valor: (v) => String(v.stock_total), clase: "num" },
      ], producto.variantes, { vacio: "Todavía no tiene tallas ni colores." })),
    form);
}

// ---------------------------------------------------------------------
// Ficha técnica (MongoDB) con vista previa de la etiqueta
// ---------------------------------------------------------------------
function convertir(texto, esLista) {
  const t = texto.trim();
  if (esLista) return t.split(",").map((x) => x.trim()).filter(Boolean);
  if (/^(sí|si|true)$/i.test(t)) return true;
  if (/^(no|false)$/i.test(t)) return false;
  if (t !== "" && !Number.isNaN(Number(t))) return Number(t);
  return t;
}
const aClave = (texto) => texto.trim().toLowerCase().replace(/\s+/g, "_").replace(/[.$]/g, "");

async function ficha(producto) {
  let actual = null;
  try { actual = await papi(`/productos/${producto.id_producto}/ficha`); } catch (e) { if (e.estado !== 404) throw e; }
  const { composicion = [], pais_origen: pais = "", ...resto } = actual?.atributos || {};

  const filasComposicion = el("div", { class: "filas-editor" });
  const filasAtributos = el("div", { class: "filas-editor" });
  const cuidados = el("textarea", { name: "cuidados", rows: 4 }, (actual?.cuidados || []).join("\n"));
  const etiquetas = el("input", { name: "etiquetas", value: (actual?.etiquetas || []).join(", ") });
  const origen = el("input", { name: "pais_origen", value: pais });
  const vistaPrevia = el("div", { class: "vista-etiqueta" });
  const zonaError = el("div");

  function filaComposicion(fibra = "", porcentaje = "") {
    const fila = el("div", { class: "fila-editor" },
      el("input", { "aria-label": "Fibra", placeholder: "algodón", value: fibra, "data-k": "fibra" }),
      el("input", { "aria-label": "Porcentaje", type: "number", min: 1, max: 100, placeholder: "%", value: porcentaje, "data-k": "porcentaje" }),
      el("button", { class: "linea__quitar", type: "button", onclick: () => { fila.remove(); refrescar(); } }, "Quitar"));
    filasComposicion.append(fila);
  }
  function filaAtributo(clave = "", valor = "") {
    const esLista = Array.isArray(valor);
    const texto = esLista ? valor.join(", ") : typeof valor === "boolean" ? (valor ? "sí" : "no") : String(valor ?? "");
    const fila = el("div", { class: "fila-editor", "data-lista": esLista ? "1" : "" },
      el("input", { "aria-label": "Atributo", placeholder: "cuello", value: clave.replaceAll("_", " "), "data-k": "clave" }),
      el("input", { "aria-label": "Valor", placeholder: "redondo", value: texto, "data-k": "valor" }),
      el("button", { class: "linea__quitar", type: "button", onclick: () => { fila.remove(); refrescar(); } }, "Quitar"));
    filasAtributos.append(fila);
  }

  function leer() {
    const atributos = {};
    const comp = [...filasComposicion.children].map((f) => ({
      fibra: f.querySelector('[data-k="fibra"]').value.trim(),
      porcentaje: Number(f.querySelector('[data-k="porcentaje"]').value),
    })).filter((c) => c.fibra && c.porcentaje);
    if (comp.length) atributos.composicion = comp;
    for (const f of filasAtributos.children) {
      const clave = aClave(f.querySelector('[data-k="clave"]').value);
      const valor = f.querySelector('[data-k="valor"]').value;
      if (clave && valor.trim()) atributos[clave] = convertir(valor, f.dataset.lista === "1");
    }
    if (origen.value.trim()) atributos.pais_origen = origen.value.trim();
    return {
      atributos,
      cuidados: cuidados.value.split("\n").map((x) => x.trim()).filter(Boolean),
      etiquetas: etiquetas.value.split(",").map((x) => x.trim()).filter(Boolean),
    };
  }

  function refrescar() {
    const datos = leer();
    const suma = (datos.atributos.composicion || []).reduce((s, c) => s + c.porcentaje, 0);
    vistaPrevia.replaceChildren(
      Object.keys(datos.atributos).length || datos.cuidados.length
        ? etiqueta(datos, { id: "vista-etiqueta" })
        : el("p", { class: "vacio" }, "La etiqueta aparece aquí mientras escribes."),
      suma && suma !== 100 ? el("p", { class: "texto-no nota" }, `La composición suma ${suma} %.`) : "");
  }

  composicion.forEach((c) => filaComposicion(c.fibra, c.porcentaje));
  if (!composicion.length) filaComposicion();
  Object.entries(resto).forEach(([k, v]) => filaAtributo(k, v));
  if (!Object.keys(resto).length) { filaAtributo(); filaAtributo(); }

  const form = el("form", { class: "tarjeta editor-ficha", novalidate: true },
    el("h2", {}, "Ficha técnica"),
    el("p", { class: "nota" }, actual ? `Versión ${actual.version}. Se guarda en MongoDB: cada prenda tiene sus propios atributos.` : "Esta prenda aún no tiene ficha. Los atributos son libres: escribe los que apliquen a esta prenda."),
    el("h3", {}, "Composición"),
    filasComposicion,
    el("button", { class: "boton boton--secundario boton--chico", type: "button", onclick: () => { filaComposicion(); } }, "Agregar fibra"),
    el("h3", {}, "Atributos"),
    el("p", { class: "nota" }, "Por ejemplo: cuello / redondo, tiro / alto, impermeable / sí, bolsillos / 5."),
    filasAtributos,
    el("button", { class: "boton boton--secundario boton--chico", type: "button", onclick: () => { filaAtributo(); } }, "Agregar atributo"),
    el("div", { class: "campos" },
      campo("País de origen", origen),
      campo("Etiquetas de búsqueda", etiquetas, "Separadas por coma: verano, básicos."),
      campo("Cuidados", cuidados, "Uno por línea.", { ancho: true })),
    zonaError,
    el("div", { class: "fila-botones" },
      el("button", { class: "boton", type: "submit" }, "Guardar ficha"),
      actual ? el("button", { class: "boton boton--peligro-texto", type: "button", onclick: eliminar }, "Eliminar ficha") : null));

  form.addEventListener("input", refrescar);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    zonaError.replaceChildren();
    const datos = leer();
    if (!Object.keys(datos.atributos).length) { errorEn(zonaError, new Error("Escribe al menos un atributo o la composición.")); return; }
    try {
      const guardada = await papi(`/productos/${producto.id_producto}/ficha`, { metodo: "PUT", cuerpo: datos });
      aviso(`Ficha guardada (versión ${guardada.version}).`);
    } catch (error) { errorEn(zonaError, error); }
  });

  async function eliminar() {
    if (!await confirmar("Eliminar ficha", "La prenda se seguirá vendiendo, pero sin ficha técnica.", { accion: "Eliminar", peligro: true })) return;
    try {
      await papi(`/productos/${producto.id_producto}/ficha`, { metodo: "DELETE" });
      aviso("Ficha eliminada.");
      location.reload();
    } catch (error) { errorEn(zonaError, error); }
  }

  refrescar();
  return el("div", { class: "editor-con-vista" }, form,
    el("aside", { class: "editor-con-vista__vista", "aria-label": "Vista previa" }, el("p", { class: "nota" }, "Así se ve en la tienda"), vistaPrevia));
}

// ---------------------------------------------------------------------
// Etiquetas QR para imprimir y colgar en las prendas
// ---------------------------------------------------------------------
function etiquetas(producto) {
  if (!producto.variantes.length) return el("div", { class: "vacio" }, el("p", {}, "Crea primero las tallas y colores."));
  return el("div", {},
    el("div", { class: "fila-botones no-imprimir" },
      el("button", { class: "boton", type: "button", onclick: () => window.print() }, "Imprimir etiquetas"),
      el("p", { class: "nota" }, "El QR abre la página de la prenda en el celular del cliente y queda registrado como escaneo.")),
    el("div", { class: "hoja-etiquetas" }, producto.variantes.map((v) =>
      el("article", { class: "colgante-impreso" },
        el("p", { class: "colgante-impreso__marca" }, "SOLSTICIO"),
        qr(`${location.origin}/escanear?codigo=${v.codigo_qr}`, { tamano: 3 }),
        el("p", { class: "colgante-impreso__codigo" }, v.codigo_qr),
        el("p", { class: "colgante-impreso__nombre" }, producto.nombre),
        el("p", {}, `Talla ${v.talla}, ${v.color.nombre}`),
        el("p", { class: "colgante-impreso__precio" }, precio(v.precio_final)),
        el("p", { class: "colgante-impreso__sku" }, v.sku)))));
}

