// Catálogo: filtros (categoría, género, búsqueda, solo disponibles), stock según
// la sede elegida y paginación con "Ver más". Los filtros viven en la URL para
// poder compartir el enlace o volver atrás sin perderlos.
import { api, el, foto, iniciarCabecera, mostrarError, precio } from "./comun.js";

const TAMANO = 12;
const resultados = document.getElementById("resultados");
const conteo = document.getElementById("conteo");
const zonaMas = document.getElementById("zona-mas");
const titulo = document.getElementById("titulo-catalogo");
const subtitulo = document.getElementById("subtitulo-catalogo");
const busquedaActiva = document.getElementById("busqueda-activa");
const soloDisponibles = document.getElementById("solo-disponibles");

let cabecera;
let pagina = 1;
let total = 0;
let cargados = [];

function filtros() {
  const p = new URLSearchParams(location.search);
  return {
    q: p.get("q") || "", categoria: p.get("categoria") || "", genero: p.get("genero") || "",
    disponibles: p.get("disponibles") === "1",
  };
}

function actualizarUrl(cambios) {
  const p = new URLSearchParams(location.search);
  for (const [clave, valor] of Object.entries(cambios)) {
    if (valor) p.set(clave, valor); else p.delete(clave);
  }
  history.replaceState(null, "", p.toString() ? `?${p}` : location.pathname);
}

const POCAS = 3; // a partir de aquí la tarjeta avisa que quedan pocas

function estadoStock(producto) {
  const tallas = producto.tallas_disponibles;
  if (producto.stock_total <= 0) {
    return [el("span", { class: "punto punto--no", "aria-hidden": "true" }),
      el("span", { class: "texto-no" }, `Agotado en ${cabecera.nombreSede()}`)];
  }
  if (producto.stock_total <= POCAS) {
    return [el("span", { class: "punto punto--pocas", "aria-hidden": "true" }),
      el("span", { class: "texto-pocas" }, `${producto.stock_total === 1 ? "Queda 1" : `Quedan ${producto.stock_total}`}, ${tallas.length === 1 ? "talla" : "tallas"} ${tallas.join(", ")}`)];
  }
  return [el("span", { class: "punto punto--si", "aria-hidden": "true" }),
    el("span", {}, `Tallas ${tallas.join(", ")}`)];
}

function tarjeta(producto) {
  return el("li", { class: producto.stock_total > 0 ? "prenda" : "prenda prenda--agotada" },
    el("a", { href: `/producto?id=${producto.id_producto}` },
      el("div", { class: "prenda__foto" }, foto(producto.imagen_principal, producto.nombre)),
      el("p", { class: "prenda__categoria" }, producto.categoria),
      el("h2", { class: "prenda__nombre" }, producto.nombre),
      el("p", { class: "prenda__precio" }, precio(producto.precio_base)),
      el("p", { class: "prenda__stock" }, ...estadoStock(producto)),
    ));
}

function pintar() {
  const { q, disponibles } = filtros();
  contarFiltros();
  titulo.textContent = `Lo que hay hoy en ${cabecera.nombreSede()}`;
  const sede = cabecera.sedes.find((s) => s.id_sede === cabecera.sedeActual());
  if (sede?.direccion) {
    subtitulo.textContent = `Mira qué tallas hay para recoger hoy en la ${sede.direccion}. Si cambias de sede arriba, el catálogo se actualiza.`;
  }
  busquedaActiva.replaceChildren(q
    ? el("span", {}, `Buscando "${q}". `, el("a", { href: "/" }, "Ver todo el catálogo"))
    : "");

  const visibles = cargados;
  if (!visibles.length) {
    resultados.replaceChildren(el("div", { class: "aviso" },
      el("p", {}, q ? `No encontramos prendas que coincidan con "${q}".`
        : disponibles ? `Con estos filtros no hay prendas disponibles en ${cabecera.nombreSede()}.`
          : "No hay prendas con estos filtros."),
      el("p", {}, disponibles ? "Prueba con otra sede o quita \"Solo lo que hay en mi sede\"." : "Prueba con otra categoría o borra la búsqueda.")));
  } else {
    resultados.replaceChildren(el("ul", { class: "rejilla" }, visibles.map(tarjeta)));
  }
  const prendas = total === 1 ? "1 prenda" : `${total} prendas`;
  conteo.textContent = disponibles ? `${prendas} con existencias en ${cabecera.nombreSede()}` : prendas;
  zonaMas.replaceChildren(cargados.length < total
    ? el("button", { class: "boton boton--secundario", type: "button", onclick: () => cargar(pagina + 1) }, "Ver más prendas")
    : "");
}

async function cargar(numero = 1) {
  const { q, categoria, genero, disponibles } = filtros();
  const parametros = new URLSearchParams({ page: numero, size: TAMANO });
  if (disponibles) parametros.set("disponibles", "true");
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
    total = datos.total;
    cargados = numero === 1 ? datos.items : cargados.concat(datos.items);
    pintar();
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

// En celular los filtros van plegados; el botón dice cuántos hay activos.
const botonFiltros = document.getElementById("boton-filtros");
const aside = document.querySelector(".filtros");
function contarFiltros() {
  const { categoria, genero, disponibles } = filtros();
  const n = [categoria, genero, disponibles].filter(Boolean).length;
  botonFiltros.textContent = n ? `Filtrar (${n} ${n === 1 ? "activo" : "activos"})` : "Filtrar";
}
botonFiltros.addEventListener("click", () => {
  const abierto = aside.classList.toggle("filtros--abierto");
  botonFiltros.setAttribute("aria-expanded", String(abierto));
});

function marcarFiltrosDesdeUrl() {
  const { genero, categoria, disponibles } = filtros();
  soloDisponibles.checked = disponibles;
  for (const radio of document.querySelectorAll('input[name="genero"]')) radio.checked = radio.value === genero;
  for (const radio of document.querySelectorAll('input[name="categoria"]')) radio.checked = radio.value === categoria;
}

document.querySelector(".filtros").addEventListener("change", (evento) => {
  const { name, value, id, checked } = evento.target;
  if (id === "solo-disponibles") {
    actualizarUrl({ disponibles: checked ? "1" : "" });
    cargar(1);
  } else if (name === "categoria" || name === "genero") {
    actualizarUrl({ [name]: value });
    cargar(1);
  }
});

async function iniciar() {
  try {
    cabecera = await iniciarCabecera({ alCambiarSede: () => cargar(1), busqueda: filtros().q });
    await cargarCategorias();
  } catch (error) {
    mostrarError(resultados, error, iniciar);
    return;
  }
  marcarFiltrosDesdeUrl();
  cargar(1);
}

iniciar();
