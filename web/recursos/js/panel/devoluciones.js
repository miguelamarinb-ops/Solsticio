// Devoluciones y cambios: lista con filtros, solicitudes de clientes por atender
// y búsqueda del pedido a devolver por el código de su comprobante.
import { el, fechaHora, precio, sinPrefijo } from "../comun.js";
import {
  campo, encabezado, insignia, opcionesSedes, paginacion, papi, selector, tabla,
} from "./ui.js";

const ESTADOS = ["SOLICITADA", "COMPLETADA", "RECHAZADA"];

export async function render(principal, ctx) {
  const q = ctx.consulta();
  const filtros = { estado: q.get("estado") || "", tipo: q.get("tipo") || "", id_sede: q.get("id_sede") || "", page: Number(q.get("page")) || 1 };
  const zona = el("div");

  function aplicar(cambios) {
    Object.assign(filtros, cambios);
    const p = new URLSearchParams(Object.entries(filtros).filter(([k, v]) => v && !(k === "page" && v === 1)));
    history.replaceState(null, "", `#/devoluciones${p.toString() ? `?${p}` : ""}`);
    cargar();
  }

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Cargando devoluciones…"));
    const p = new URLSearchParams({ page: filtros.page, size: 20 });
    for (const k of ["estado", "tipo", "id_sede"]) if (filtros[k]) p.set(k, filtros[k]);
    const datos = await papi(`/devoluciones?${p}`);
    zona.replaceChildren(
      tabla([
        { titulo: "N.º", valor: (d) => el("a", { href: `#/devoluciones/${d.id_devolucion}` }, `#${d.id_devolucion}`) },
        { titulo: "Fecha", valor: (d) => fechaHora(d.fecha_solicitud) },
        { titulo: "Pedido", valor: (d) => d.codigo_pedido },
        { titulo: "Tipo", valor: (d) => insignia(d.tipo) },
        { titulo: "Cliente", valor: (d) => (d.cliente ? `${d.cliente.nombres} ${d.cliente.apellidos || ""}` : "Sin identificar") },
        { titulo: "Sede", valor: (d) => sinPrefijo(d.sede.nombre) },
        { titulo: "Nota crédito", valor: (d) => (d.nota_credito ? precio(d.nota_credito.monto) : "—"), clase: "num" },
        { titulo: "Estado", valor: (d) => insignia(d.estado) },
      ], datos.items, { vacio: "No hay devoluciones con estos filtros.", alClic: (d) => ctx.navegar(`#/devoluciones/${d.id_devolucion}`) }),
      paginacion({ pagina: datos.page, total: datos.total, tamano: datos.size, alCambiar: (n) => aplicar({ page: n }) }));
  }

  const busqueda = el("form", { class: "busqueda-codigo", role: "search" },
    el("label", { for: "buscar-devolver", class: "solo-lector" }, "Código del pedido a devolver"),
    el("input", { id: "buscar-devolver", name: "codigo", placeholder: "SOL-P-00000001", autocomplete: "off" }),
    el("button", { class: "boton", type: "submit" }, "Registrar devolución"));
  busqueda.addEventListener("submit", (e) => {
    e.preventDefault();
    const codigo = busqueda.codigo.value.trim().toUpperCase();
    if (codigo) ctx.navegar(`#/devoluciones/nueva?codigo=${encodeURIComponent(codigo)}`);
  });

  const barra = el("div", { class: "filtros-barra" },
    campo("Estado", selector("estado", [["", "Todos"], ...ESTADOS.map((e) => [e, insignia(e).textContent])], filtros.estado,
      { onchange: (e) => aplicar({ estado: e.target.value, page: 1 }) })),
    campo("Tipo", selector("tipo", [["", "Todos"], ["DEVOLUCION", "Devolución"], ["CAMBIO", "Cambio"]], filtros.tipo,
      { onchange: (e) => aplicar({ tipo: e.target.value, page: 1 }) })),
    ctx.esAdmin ? campo("Sede", selector("id_sede", opcionesSedes(ctx.sedes, "Todas"), filtros.id_sede,
      { onchange: (e) => aplicar({ id_sede: e.target.value, page: 1 }) })) : null,
    busqueda);

  principal.replaceChildren(
    encabezado("Devoluciones y cambios",
      "Escribe o escanea el código del comprobante para recibir prendas. Las solicitudes de los clientes aparecen como “Solicitada”."),
    barra, zona);
  await cargar();
}
