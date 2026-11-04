// Prendas del catálogo (administración), incluidas las desactivadas.
import { el, foto, precio } from "../comun.js";
import { campo, encabezado, insignia, paginacion, papi, selector, tabla } from "./ui.js";

export async function render(principal, ctx) {
  const filtros = { q: "", categoria: "", page: 1 };
  const categorias = await papi("/categorias");
  const zona = el("div");

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Cargando prendas…"));
    const p = new URLSearchParams({ page: filtros.page, size: 20, inactivos: "true" });
    if (filtros.q) p.set("q", filtros.q);
    if (filtros.categoria) p.set("categoria", filtros.categoria);
    const datos = await papi(`/productos?${p}`);
    zona.replaceChildren(
      tabla([
        { titulo: "", valor: (x) => el("span", { class: "miniatura" }, foto(x.imagen_principal, x.nombre)), clase: "col-miniatura" },
        { titulo: "Prenda", valor: (x) => el("a", { href: `#/productos/${x.id_producto}` }, x.nombre) },
        { titulo: "Categoría", valor: (x) => x.categoria },
        { titulo: "Para", valor: (x) => insignia(x.genero, "gris") },
        { titulo: "Precio", valor: (x) => precio(x.precio_base), clase: "num" },
        { titulo: "Existencias", valor: (x) => String(x.stock_total), clase: "num" },
        { titulo: "Estado", valor: (x) => insignia(x.activo ? "ACTIVO" : "INACTIVO") },
      ], datos.items, { vacio: "No hay prendas con estos filtros.", alClic: (x) => ctx.navegar(`#/productos/${x.id_producto}`) }),
      paginacion({ pagina: datos.page, total: datos.total, tamano: datos.size, alCambiar: (n) => { filtros.page = n; cargar(); } }));
  }

  const buscador = el("input", { type: "search", placeholder: "Nombre de la prenda" });
  let espera;
  buscador.addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(() => { filtros.q = buscador.value.trim(); filtros.page = 1; cargar(); }, 300); });

  principal.replaceChildren(
    encabezado("Prendas", "Precios, variantes, fichas técnicas y etiquetas QR.", el("a", { class: "boton", href: "#/productos/nuevo" }, "Nueva prenda")),
    el("div", { class: "filtros-barra" },
      campo("Buscar", buscador),
      campo("Categoría", selector("categoria", [["", "Todas"], ...categorias.map((c) => [c.id_categoria, c.nombre])], "",
        { onchange: (e) => { filtros.categoria = e.target.value; filtros.page = 1; cargar(); } }))),
    zona);
  await cargar();
}
