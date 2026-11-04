// Componentes del panel: sesión, llamadas con token, avisos, diálogos, tablas,
// formularios y el buscador de variantes que usan mostrador, ingresos y traslados.
import { api, el, ErrorApi, listaConflictos, precio, sinPrefijo } from "../comun.js";

// ---------------------------------------------------------------------
// Sesión (sessionStorage: se cierra al cerrar la pestaña)
// ---------------------------------------------------------------------
const CLAVE = "solsticio.panel";
export const sesion = {
  leer() {
    try {
      const datos = JSON.parse(sessionStorage.getItem(CLAVE) || "null");
      return datos && datos.expira > Date.now() ? datos : null;
    } catch { return null; }
  },
  guardar(token, usuario, segundos) {
    try { sessionStorage.setItem(CLAVE, JSON.stringify({ token, usuario, expira: Date.now() + segundos * 1000 })); } catch { /* sin almacenamiento */ }
  },
  cerrar() { try { sessionStorage.removeItem(CLAVE); } catch { /* nada */ } },
};

let alExpirar = () => {};
export const configurarExpiracion = (fn) => { alExpirar = fn; };

export async function papi(ruta, opciones = {}) {
  try {
    return await api(ruta, { ...opciones, token: sesion.leer()?.token });
  } catch (error) {
    if (error.estado === 401 && !ruta.startsWith("/auth/login")) {
      sesion.cerrar();
      alExpirar("Tu sesión terminó. Vuelve a iniciar sesión.");
    }
    throw error;
  }
}

// ---------------------------------------------------------------------
// Avisos (toast) y diálogos nativos <dialog>
// ---------------------------------------------------------------------
export function aviso(mensaje, tipo = "ok") {
  const zona = document.getElementById("avisos");
  const nodo = el("div", { class: `toast toast--${tipo}`, role: tipo === "error" ? "alert" : "status" }, mensaje);
  zona.append(nodo);
  setTimeout(() => nodo.classList.add("toast--saliendo"), 4200);
  setTimeout(() => nodo.remove(), 4600);
}

export function avisoError(error) {
  aviso(error.message || "Algo salió mal", "error");
}

// Bloque de error dentro de un formulario, con el detalle de existencias si lo hay.
export function errorEn(contenedor, error) {
  contenedor.replaceChildren(el("div", { class: "aviso aviso--error", role: "alert" },
    el("p", {}, error.message),
    error.cuerpo?.conflictos ? listaConflictos(error.cuerpo.conflictos) : null,
    error.cuerpo?.permitidos ? el("p", {}, `Opciones válidas: ${error.cuerpo.permitidos.join(", ")}.`) : null,
    error.cuerpo?.campos ? el("p", {}, `Revisa: ${error.cuerpo.campos.join(", ")}.`) : null));
}

export function dialogo({ titulo, contenido, acciones = [] }) {
  const d = el("dialog", { class: "dialogo", "aria-labelledby": "titulo-dialogo" },
    el("h2", { id: "titulo-dialogo" }, titulo),
    el("div", { class: "dialogo__cuerpo" }, contenido),
    el("div", { class: "dialogo__acciones" }, acciones));
  document.body.append(d);
  d.addEventListener("close", () => d.remove());
  d.showModal();
  return d;
}

export function confirmar(titulo, texto, { accion = "Confirmar", peligro = false } = {}) {
  return new Promise((resolver) => {
    let respuesta = false;
    const d = dialogo({
      titulo, contenido: el("p", {}, texto),
      acciones: [
        el("button", { class: "boton boton--secundario", type: "button", onclick: () => d.close() }, "Cancelar"),
        el("button", { class: `boton${peligro ? " boton--peligro" : ""}`, type: "button", onclick: () => { respuesta = true; d.close(); } }, accion),
      ],
    });
    d.addEventListener("close", () => resolver(respuesta));
  });
}

// ---------------------------------------------------------------------
// Piezas de página
// ---------------------------------------------------------------------
export function encabezado(titulo, descripcion, ...acciones) {
  return el("header", { class: "pagina__cabeza" },
    el("div", {}, el("h1", { tabindex: "-1" }, titulo), descripcion ? el("p", {}, descripcion) : null),
    acciones.length ? el("div", { class: "pagina__acciones" }, acciones) : null);
}

export function pestanas(items, actual) {
  return el("nav", { class: "pestanas", "aria-label": "Secciones" }, items.map(([href, texto]) =>
    el("a", { href, "aria-current": href === actual ? "page" : null }, texto)));
}

const TONOS = {
  PENDIENTE: "sol", PAGADO: "verde", PREPARANDO: "azul", ENVIADO: "azul", ENTREGADO: "gris", CANCELADO: "rojo",
  SOLICITADO: "sol", EN_TRANSITO: "azul", RECIBIDO: "verde",
  APROBADO: "verde", RECHAZADO: "rojo", VALIDADA: "verde", RECHAZADA: "rojo",
  PUBLICADA: "verde", OCULTA: "gris", ACTIVO: "verde", INACTIVO: "gris",
  INGRESO: "verde", VENTA: "azul", DEVOLUCION: "sol", TRASLADO_SALIDA: "sol", TRASLADO_ENTRADA: "verde", AJUSTE: "gris",
  WEB: "azul", TIENDA: "gris",
};
const TEXTOS = {
  EN_TRANSITO: "En tránsito", TRASLADO_SALIDA: "Salida por traslado", TRASLADO_ENTRADA: "Entrada por traslado",
  RECOGER_EN_TIENDA: "Recoger en tienda", DOMICILIO: "Domicilio", INMEDIATA: "Entrega inmediata", DEVOLUCION: "Devolución",
};
export const legible = (valor) => TEXTOS[valor] || (valor ? valor.charAt(0) + valor.slice(1).toLowerCase().replaceAll("_", " ") : "");

export function insignia(valor, tono) {
  return el("span", { class: `insignia insignia--${tono || TONOS[valor] || "gris"}` }, legible(valor));
}

// columnas: [{ titulo, valor: (fila) => nodo|texto, clase }]
export function tabla(columnas, filas, { vacio = "No hay datos para mostrar.", alClic } = {}) {
  if (!filas.length) return el("div", { class: "vacio" }, el("p", {}, vacio));
  return el("div", { class: "tabla-caja" }, el("table", { class: "tabla" },
    el("thead", {}, el("tr", {}, columnas.map((c) => el("th", { scope: "col", class: c.clase }, c.titulo)))),
    el("tbody", {}, filas.map((fila) => {
      const tr = el("tr", { class: alClic ? "fila-enlace" : null },
        columnas.map((c) => el("td", { class: c.clase, "data-titulo": c.titulo }, c.valor(fila))));
      if (alClic) tr.addEventListener("click", (e) => { if (!e.target.closest("a,button,input,select")) alClic(fila); });
      return tr;
    }))));
}

export function paginacion({ pagina, total, tamano, alCambiar }) {
  const paginas = Math.max(1, Math.ceil(total / tamano));
  if (paginas <= 1) return el("p", { class: "paginacion" }, `${total} ${total === 1 ? "registro" : "registros"}`);
  return el("nav", { class: "paginacion", "aria-label": "Paginación" },
    el("button", { class: "boton boton--secundario boton--chico", type: "button", disabled: pagina <= 1, onclick: () => alCambiar(pagina - 1) }, "Anterior"),
    el("span", {}, `Página ${pagina} de ${paginas} (${total} registros)`),
    el("button", { class: "boton boton--secundario boton--chico", type: "button", disabled: pagina >= paginas, onclick: () => alCambiar(pagina + 1) }, "Siguiente"));
}

let idCampo = 0;
export function campo(texto, control, ayuda, { ancho = false } = {}) {
  if (!control.id) control.id = `c${++idCampo}`;
  return el("div", { class: `campo${ancho ? " campo--ancho" : ""}` },
    el("label", { for: control.id }, texto), control, ayuda ? el("small", {}, ayuda) : null);
}

export function selector(nombre, opciones, valor, atributos = {}) {
  return el("select", { name: nombre, ...atributos }, opciones.map(([v, texto]) =>
    el("option", { value: v, selected: String(v) === String(valor ?? "") }, texto)));
}

export const opcionesSedes = (sedes, todas) =>
  [...(todas ? [["", todas]] : []), ...sedes.map((s) => [s.id_sede, sinPrefijo(s.nombre)])];

export function cargando(texto = "Cargando…") {
  return el("p", { class: "cargando" }, texto);
}

export function datos(pares) {
  return el("dl", { class: "datos" }, pares.filter(Boolean).flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v ?? "—")]));
}

// ---------------------------------------------------------------------
// Buscador de variantes: por código QR/SKU o por nombre de la prenda
// ---------------------------------------------------------------------
export function buscadorVariantes({ alElegir, sede = () => null, textoBoton = "Agregar" }) {
  const entrada = el("input", { type: "search", placeholder: "Código SOL-V-… o nombre de la prenda", autocomplete: "off", "aria-label": "Buscar prenda" });
  const resultados = el("div", { class: "buscador-variantes__resultados", "aria-live": "polite" });

  function botonVariante(v, producto) {
    const enSede = sede() ? v.disponibilidad?.find((d) => d.id_sede === sede())?.cantidad : null;
    return el("button", {
      class: "variante-opcion", type: "button",
      onclick: () => alElegir({
        id_variante: v.id_variante, sku: v.sku, codigo_qr: v.codigo_qr,
        descripcion: `${producto.nombre} - ${v.talla} - ${v.color.nombre ?? v.color}`,
        precio: v.precio_final, producto: producto.nombre, id_producto: producto.id_producto,
      }),
    },
    el("strong", {}, `${v.talla}, ${v.color.nombre ?? v.color}`),
    el("span", {}, v.sku),
    el("span", {}, precio(v.precio_final)),
    enSede != null ? el("span", { class: enSede ? "texto-si" : "texto-no" }, enSede ? `${enSede} en sede` : "Sin existencias") : null,
    el("span", { class: "variante-opcion__accion" }, textoBoton));
  }

  async function buscar() {
    const texto = entrada.value.trim();
    if (!texto) { resultados.replaceChildren(); return; }
    resultados.replaceChildren(cargando("Buscando…"));
    try {
      if (/^SOL-V-/i.test(texto)) {
        const v = await papi(`/variantes/qr/${encodeURIComponent(texto.toUpperCase())}`);
        const producto = await papi(`/productos/${v.producto.id_producto}`);
        const variante = producto.variantes.find((x) => x.id_variante === v.id_variante);
        resultados.replaceChildren(el("div", { class: "variantes-de" }, el("p", {}, producto.nombre), botonVariante(variante, producto)));
        return;
      }
      const lista = await papi(`/productos?q=${encodeURIComponent(texto)}&size=8`);
      if (!lista.items.length) { resultados.replaceChildren(el("p", { class: "nota" }, "No hay prendas con ese nombre.")); return; }
      const detalles = await Promise.all(lista.items.map((p) => papi(`/productos/${p.id_producto}`)));
      resultados.replaceChildren(...detalles.map((producto) => el("div", { class: "variantes-de" },
        el("p", {}, producto.nombre),
        producto.variantes.length
          ? el("div", { class: "variantes-de__lista" }, producto.variantes.map((v) => botonVariante(v, producto)))
          : el("p", { class: "nota" }, "Sin variantes."))));
    } catch (error) {
      resultados.replaceChildren(el("p", { class: "texto-no" }, error.estado === 404 ? "Ese código no corresponde a ninguna prenda." : error.message));
    }
  }

  let espera;
  entrada.addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(buscar, 300); });
  entrada.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); clearTimeout(espera); buscar(); } });
  return el("div", { class: "buscador-variantes" }, entrada, resultados);
}

export { ErrorApi };
