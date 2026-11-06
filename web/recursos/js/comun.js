// Utilidades compartidas por la tienda y el panel: llamadas a la API, formato,
// cabecera de la tienda y carrito. Todo el contenido que viene de la API (sobre
// todo las opiniones, que escriben los clientes) se inserta con textContent a
// través de el(); nunca con innerHTML.

export const API = "/api/v1";

export class ErrorApi extends Error {
  constructor(estado, cuerpo) {
    super((cuerpo && cuerpo.detail) || `Error ${estado}`);
    this.estado = estado;
    this.cuerpo = cuerpo || {};
  }
}

export async function api(ruta, { metodo = "GET", cuerpo, token } = {}) {
  const cabeceras = {};
  if (cuerpo) cabeceras["Content-Type"] = "application/json";
  if (token) cabeceras.Authorization = `Bearer ${token}`;
  let respuesta;
  try {
    respuesta = await fetch(API + ruta, {
      method: metodo, headers: cabeceras, body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    });
  } catch {
    throw new ErrorApi(0, { detail: "No hay conexión con la tienda. Revisa tu internet e inténtalo de nuevo." });
  }
  const texto = await respuesta.text();
  let datos = null;
  try { datos = texto ? JSON.parse(texto) : null; } catch { datos = { detail: texto }; }
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, datos);
  return datos;
}

// Crea un elemento: el("p", { class: "x", onclick: fn }, "texto", otroNodo, [lista])
export function el(etiqueta, atributos = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos || {})) {
    if (valor === false || valor == null) continue;
    if (clave.startsWith("on") && typeof valor === "function") nodo.addEventListener(clave.slice(2), valor);
    else if (clave === "value" && "value" in nodo) nodo.value = valor;
    else if (valor === true) nodo.setAttribute(clave, "");
    else nodo.setAttribute(clave, valor);
  }
  for (const hijo of hijos.flat(Infinity)) {
    if (hijo == null || hijo === false || hijo === "") continue;
    nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
  return nodo;
}

const formatoPeso = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
export const precio = (valor) => formatoPeso.format(Number(valor) || 0);

const formatoFecha = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", year: "numeric" });
const formatoFechaHora = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
export const fecha = (iso) => (iso ? formatoFecha.format(new Date(iso)) : "");
export const fechaHora = (iso) => (iso ? formatoFechaHora.format(new Date(iso)) : "");

export const sinPrefijo = (nombreSede) => (nombreSede || "").replace(/^Solsticio\s+/, "");

export function estrellas(n) {
  const llenas = Math.round(n);
  return el("span", { class: "estrellas", role: "img", "aria-label": `${n} de 5 estrellas` },
    "★".repeat(llenas) + "☆".repeat(5 - llenas));
}

// Imagen del producto o, si no hay o no carga, la silueta de etiqueta con la inicial.
export function foto(url, nombre, { lazy = true } = {}) {
  const marcador = () => el("div", { class: "sin-foto", "aria-hidden": "true" }, (nombre || "?").charAt(0));
  if (!url) return marcador();
  const img = el("img", { src: url, alt: nombre, loading: lazy ? "lazy" : "eager", decoding: "async" });
  img.addEventListener("error", () => img.replaceWith(marcador()));
  return img;
}

// Código QR como SVG (librería qrcode-generator cargada en la página). Si no está, muestra el texto.
export function qr(texto, { tamano = 4 } = {}) {
  if (typeof window.qrcode !== "function") return el("code", { class: "qr-texto" }, texto);
  const codigo = window.qrcode(0, "M");
  codigo.addData(texto);
  codigo.make();
  const caja = el("div", { class: "qr", role: "img", "aria-label": `Código QR ${texto}` });
  // createSvgTag genera el SVG a partir del texto codificado (no de HTML externo).
  caja.innerHTML = codigo.createSvgTag({ cellSize: tamano, margin: 0, scalable: true });
  return caja;
}

// Marca los campos con error para lectores de pantalla y lleva el cursor al primero.
// La marca se quita sola cuando la persona corrige el campo.
export function marcarInvalidos(form, nombres) {
  for (const campo of form.querySelectorAll('[aria-invalid="true"]')) campo.removeAttribute("aria-invalid");
  const campos = nombres.map((n) => form.elements[n]).filter(Boolean)
    .map((c) => (c instanceof RadioNodeList ? c[0] : c));
  for (const campo of campos) {
    campo.setAttribute("aria-invalid", "true");
    campo.addEventListener("input", () => campo.removeAttribute("aria-invalid"), { once: true });
  }
  campos[0]?.focus();
}

export function mostrarError(contenedor, error, reintentar) {
  contenedor.replaceChildren(el("div", { class: "aviso aviso--error", role: "alert" },
    el("p", {}, error.message),
    error.cuerpo?.conflictos ? listaConflictos(error.cuerpo.conflictos) : null,
    reintentar ? el("p", {}, el("button", { class: "boton boton--secundario", type: "button", onclick: reintentar }, "Intentar de nuevo")) : null,
  ));
}

// Detalle de un 409 "Existencias insuficientes": qué falta y dónde sí hay.
export function listaConflictos(conflictos) {
  return el("ul", { class: "conflictos" }, conflictos.map((c) => el("li", {},
    `${c.sku}: pediste ${c.solicitado}, hay ${c.disponible}.`,
    c.otras_sedes?.length
      ? ` Disponible en ${c.otras_sedes.map((s) => `${sinPrefijo(s.nombre)} (${s.disponible})`).join(", ")}.`
      : "")));
}

// ---------------------------------------------------------------------
// Almacenamiento local (sede elegida y carrito). Puede fallar en modo privado.
// ---------------------------------------------------------------------
function leer(clave, defecto) {
  try { const v = localStorage.getItem(clave); return v ? JSON.parse(v) : defecto; } catch { return defecto; }
}
function escribir(clave, valor) {
  try { localStorage.setItem(clave, JSON.stringify(valor)); } catch { /* sin almacenamiento */ }
}

export const sedeGuardada = () => leer("solsticio.sede", null);

// Sesión del cliente registrado (rol CLIENTE). Distinta de la del panel del
// personal: el cliente la conserva entre visitas hasta que vence el token.
export const sesionCliente = {
  leer() {
    const datos = leer("solsticio.cliente", null);
    return datos && datos.expira > Date.now() ? datos : null;
  },
  guardar(token, usuario, segundos) {
    escribir("solsticio.cliente", { token, usuario, expira: Date.now() + segundos * 1000 });
  },
  cerrar() { try { localStorage.removeItem("solsticio.cliente"); } catch { /* nada */ } },
};

// Carrito: [{id_variante, id_producto, nombre, talla, color, precio, imagen, cantidad}]
export const carrito = {
  items: () => leer("solsticio.carrito", []),
  guardar(items) { escribir("solsticio.carrito", items); actualizarContadorCarrito(); },
  agregar(item, cantidad = 1) {
    const items = carrito.items();
    const existente = items.find((i) => i.id_variante === item.id_variante);
    if (existente) existente.cantidad += cantidad; else items.push({ ...item, cantidad });
    carrito.guardar(items);
  },
  cambiar(idVariante, cantidad) {
    carrito.guardar(carrito.items()
      .map((i) => (i.id_variante === idVariante ? { ...i, cantidad } : i))
      .filter((i) => i.cantidad > 0));
  },
  vaciar() { carrito.guardar([]); },
  unidades: () => carrito.items().reduce((suma, i) => suma + i.cantidad, 0),
  total: () => carrito.items().reduce((suma, i) => suma + i.precio * i.cantidad, 0),
};

function actualizarContadorCarrito() {
  const contador = document.getElementById("contador-carrito");
  if (!contador) return;
  const n = carrito.unidades();
  contador.textContent = n ? String(n) : "";
  contador.hidden = !n;
  contador.closest("a")?.setAttribute("aria-label", n ? `Carrito, ${n} ${n === 1 ? "prenda" : "prendas"}` : "Carrito vacío");
}

// ---------------------------------------------------------------------
// Cabecera de la tienda (se arma igual en todas las páginas)
// ---------------------------------------------------------------------
export async function iniciarCabecera({ alCambiarSede, busqueda = "" } = {}) {
  const cabecera = document.querySelector("[data-cabecera]");
  const actual = location.pathname;
  const enlace = (href, texto, extra) => el("a", {
    href, class: "nav-tienda__enlace", "aria-current": actual === href ? "page" : null,
  }, texto, extra);

  const selector = el("select", { id: "sede" }, el("option", {}, "Cargando…"));
  cabecera.replaceChildren(el("div", { class: "cabecera__interior" },
    el("a", { class: "marca", href: "/" }, "SOLSTICIO"),
    el("form", { class: "buscador", role: "search", action: "/" },
      el("label", { class: "solo-lector", for: "q" }, "Buscar prendas"),
      el("input", { id: "q", name: "q", type: "search", placeholder: "Buscar prendas", autocomplete: "off", value: busqueda }),
      el("button", { type: "submit" }, "Buscar")),
    el("div", { class: "selector-sede" }, el("label", { for: "sede" }, "Tu sede"), selector),
    el("nav", { class: "nav-tienda", "aria-label": "Tienda" },
      enlace("/escanear", "Escanear QR"),
      enlace("/cuenta", sesionCliente.leer() ? "Mi cuenta" : "Entrar"),
      enlace("/carrito", "Carrito", el("span", { class: "contador", id: "contador-carrito", hidden: true }))),
  ));
  actualizarContadorCarrito();

  const sedes = await api("/sedes");
  let elegida = sedeGuardada();
  if (!sedes.some((s) => s.id_sede === elegida)) elegida = sedes[0]?.id_sede ?? null;
  selector.replaceChildren(...sedes.map((s) =>
    el("option", { value: s.id_sede, selected: s.id_sede === elegida }, sinPrefijo(s.nombre))));
  if (elegida) escribir("solsticio.sede", elegida);
  selector.addEventListener("change", () => {
    escribir("solsticio.sede", Number(selector.value));
    alCambiarSede?.(Number(selector.value));
  });
  return {
    sedes,
    sedeActual: () => Number(selector.value) || null,
    nombreSede: () => sinPrefijo(sedes.find((s) => s.id_sede === Number(selector.value))?.nombre) || "tu sede",
  };
}
