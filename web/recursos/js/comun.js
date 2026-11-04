// Utilidades compartidas de la tienda: llamadas a la API, formato y cabecera.
// Todo el contenido que viene de la API (sobre todo las reseñas, que escriben
// los clientes) se inserta con textContent a través de el(); nunca con innerHTML.

export const API = "/api/v1";
const CLAVE_SEDE = "solsticio.sede";

export class ErrorApi extends Error {
  constructor(estado, cuerpo) {
    super((cuerpo && cuerpo.detail) || `Error ${estado}`);
    this.estado = estado;
    this.cuerpo = cuerpo || {};
  }
}

export async function api(ruta, { metodo = "GET", cuerpo } = {}) {
  let respuesta;
  try {
    respuesta = await fetch(API + ruta, {
      method: metodo,
      headers: cuerpo ? { "Content-Type": "application/json" } : {},
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    });
  } catch {
    throw new ErrorApi(0, { detail: "No hay conexión con la tienda. Revisa tu internet e inténtalo de nuevo." });
  }
  const texto = await respuesta.text();
  const datos = texto ? JSON.parse(texto) : null;
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, datos);
  return datos;
}

// Crea un elemento: el("p", { class: "x" }, "texto", otroNodo)
export function el(etiqueta, atributos = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) {
    if (valor === false || valor == null) continue;
    if (clave.startsWith("on")) nodo.addEventListener(clave.slice(2), valor);
    else if (valor === true) nodo.setAttribute(clave, "");
    else nodo.setAttribute(clave, valor);
  }
  for (const hijo of hijos.flat()) {
    if (hijo == null || hijo === false) continue;
    nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
  return nodo;
}

const formatoPeso = new Intl.NumberFormat("es-CO", {
  style: "currency", currency: "COP", maximumFractionDigits: 0,
});
export const precio = (valor) => formatoPeso.format(valor);

const formatoFecha = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric" });
export const fecha = (iso) => formatoFecha.format(new Date(iso));

export function estrellas(n) {
  const llenas = Math.round(n);
  return el("span", { class: "estrellas", "aria-label": `${n} de 5 estrellas` },
    "★".repeat(llenas) + "☆".repeat(5 - llenas));
}

// Imagen del producto o, si no hay o no carga, la silueta de etiqueta con la inicial.
export function foto(url, nombre) {
  const marcador = () => el("div", { class: "sin-foto", "aria-hidden": "true" }, (nombre || "?").charAt(0));
  if (!url) return marcador();
  const img = el("img", { src: url, alt: nombre, loading: "lazy" });
  img.addEventListener("error", () => img.replaceWith(marcador()));
  return img;
}

// ---------------------------------------------------------------------
// Sede elegida (se recuerda en este navegador)
// ---------------------------------------------------------------------
export function sedeGuardada() {
  try { return Number(localStorage.getItem(CLAVE_SEDE)) || null; } catch { return null; }
}
function guardarSede(id) {
  try { localStorage.setItem(CLAVE_SEDE, String(id)); } catch { /* sin almacenamiento */ }
}

// Llena el selector de sede de la cabecera y avisa cuando cambia.
export async function iniciarCabecera({ alCambiarSede } = {}) {
  const selector = document.getElementById("sede");
  const sedes = await api("/sedes");
  let actual = sedeGuardada();
  if (!sedes.some((s) => s.id_sede === actual)) actual = sedes[0]?.id_sede ?? null;
  selector.replaceChildren(...sedes.map((s) =>
    el("option", { value: s.id_sede, selected: s.id_sede === actual }, s.nombre.replace(/^Solsticio\s+/, ""))));
  if (actual) guardarSede(actual);
  selector.addEventListener("change", () => {
    guardarSede(Number(selector.value));
    alCambiarSede?.(Number(selector.value));
  });
  return { sedes, sedeActual: () => Number(selector.value) || null };
}

export function mostrarError(contenedor, error, reintentar) {
  contenedor.replaceChildren(el("div", { class: "aviso aviso--error", role: "alert" },
    el("p", {}, error.message),
    reintentar ? el("p", {}, el("button", { class: "boton boton--secundario", type: "button", onclick: reintentar }, "Intentar de nuevo")) : null,
  ));
}
