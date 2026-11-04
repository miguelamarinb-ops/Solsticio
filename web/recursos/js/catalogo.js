// Catálogo: filtros (categoría, género, búsqueda), stock según la sede elegida
// y paginación con "Ver más". El estado de los filtros vive en la URL para que
// se pueda compartir el enlace o volver atrás sin perderlos.
import { api, el, foto, iniciarCabecera, mostrarError, precio } from "./comun.js";

const TAMANO = 12;
const resultados = document.getElementById("resultados");
const conteo = document.getElementById("conteo");
const zonaMas = document.getElementById("zona-mas");
const formBusqueda = document.getElementById("form-busqueda");
const campoBusqueda = document.getElementById("q");

let cabecera;
let pagina = 1;
let cargados = [];

function filtros() {
  const p = new URLSearchParams(location.search);
  return { q: p.get("q") || "", categoria: p.get("categoria") || "", genero: p.get("genero") || "" };
}

function actualizarUrl(cambios) {
  const p = new URLSearchParams(location.search);
  for (const [clave, valor] of Object.entries(cambios)) {
    if (valor) p.set(clave, valor); else p.delete(clave);
  }
  history.replaceState(null, "", p.toString() ? `?${p}` : location.pathname);
}

function nombreSede() {
  const opcion = document.querySelector("#sede option:checked");
  return opcion ? opcion.textContent : "tu sede";
}

function tarjeta(producto) {
  const hay = producto.stock_total > 0;
  return el("li", { class: "prenda" },
    el("a", { href: `/producto?id=${producto.id_producto}` },
      el("div", { class: "prenda__foto" }, foto(producto.imagen_principal, producto.nombre)),
      el("p", { class: "prenda__categoria" }, producto.categoria),
      el("h2", { class: "prenda__nombre" }, producto.nombre),
      el("p", { class: "prenda__precio" }, precio(producto.precio_base)),
      el("p", { class: "prenda__stock" },
        el("span", { class: `punto ${hay ? "punto--si" : "punto--no"}`, "aria-hidden": "true" }),
        hay
          ? el("span", {}, `Tallas ${producto.tallas_disponibles.join(", ")} en ${nombreSede()}`)
          : el("span", { class: "texto-no" }, `Agotado en ${nombreSede()}`)),
    ));
}

function pintar(total) {
  if (!cargados.length) {
    const { q } = filtros();
    resultados.replaceChildren(el("div", { class: "aviso" },
      el("p", {}, q ? `No encontramos prendas que coincidan con "${q}".` : "No hay prendas con estos filtros."),
      el("p", {}, "Prueba con otra categoría o borra la búsqueda.")));
    conteo.textContent = "";
    zonaMas.replaceChildren();
    return;
  }
  resultados.replaceChildren(el("ul", { class: "rejilla" }, cargados.map(tarjeta)));
  conteo.textContent = total === 1 ? "1 prenda" : `${total} prendas`;
  zonaMas.replaceChildren(cargados.length < total
    ? el("button", { class: "boton boton--secundario", type: "button", onclick: () => cargar(pagina + 1) }, "Ver más prendas")
    : "");
}

async function cargar(numero = 1) {
  const { q, categoria, genero } = filtros();
  const parametros = new URLSearchParams({ page: numero, size: TAMANO });
  if (q) parametros.set("q", q);
  if (categoria) parametros.set("categoria", categoria);
  if (genero) parametros.set("genero", genero);
  const sede = cabecera?.sedeActual();
  if (sede) parametros.set("sede", sede);

  if (numero === 1) {
    resultados.replaceChildren(el("p", { class: "cargando" }, "Cargando prendas…"));
    zonaMas.replaceChildren();
  }
  try {
    const datos = await api(`/productos?${parametros}`);
    pagina = numero;
    cargados = numero === 1 ? datos.items : cargados.concat(datos.items);
    pintar(datos.total);
  } catch (error) {
    mostrarError(resultados, error, () => cargar(1));
  }
}

async function cargarCategorias() {
  const contenedor = document.getElementById("filtro-categoria");
  const actual = filtros().categoria;
  const categorias = await api("/categorias");
  contenedor.append(...categorias.map((c) => el("label", {},
    el("input", { type: "radio", name: "categoria", value: c.id_categoria, checked: String(c.id_categoria) === actual }),
    " ", c.nombre)));
}

function marcarFiltrosDesdeUrl() {
  const { q, genero, categoria } = filtros();
  campoBusqueda.value = q;
  for (const radio of document.querySelectorAll('input[name="genero"]')) radio.checked = radio.value === genero;
  for (const radio of document.querySelectorAll('input[name="categoria"]')) radio.checked = radio.value === categoria;
}

document.querySelector(".filtros").addEventListener("change", (evento) => {
  const { name, value } = evento.target;
  if (name === "categoria" || name === "genero") {
    actualizarUrl({ [name]: value });
    cargar(1);
  }
});

formBusqueda.addEventListener("submit", (evento) => {
  evento.preventDefault();
  actualizarUrl({ q: campoBusqueda.value.trim() });
  cargar(1);
});

async function iniciar() {
  try {
    cabecera = await iniciarCabecera({ alCambiarSede: () => cargar(1) });
    await cargarCategorias();
  } catch (error) {
    mostrarError(resultados, error, iniciar);
    return;
  }
  marcarFiltrosDesdeUrl();
  cargar(1);
}

iniciar();
