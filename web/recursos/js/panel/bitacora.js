// Bitácora de actividad (MongoDB, colección actividad_usuario). Cada petición
// hecha con sesión queda registrada con su resultado.
import { el, fechaHora } from "../comun.js";
import { campo, encabezado, legible, paginacion, papi, selector, tabla } from "./ui.js";

export async function render(principal, ctx) {
  const q = ctx.consulta();
  const usuarios = await papi("/usuarios");
  const nombres = Object.fromEntries(usuarios.map((u) => [u.id_usuario, `${u.nombres} ${u.apellidos}`]));
  const filtros = { id_usuario: q.get("id_usuario") || "", accion: "", exito: "", desde: "", hasta: "", page: 1 };
  const zona = el("div");

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Cargando bitácora…"));
    const p = new URLSearchParams({ page: filtros.page, size: 25 });
    for (const k of ["id_usuario", "accion", "exito", "desde", "hasta"]) if (filtros[k]) p.set(k, filtros[k]);
    const datos = await papi(`/actividad?${p}`);
    zona.replaceChildren(
      tabla([
        { titulo: "Cuándo", valor: (a) => fechaHora(a.fecha) },
        { titulo: "Quién", valor: (a) => nombres[a.id_usuario] || `Usuario ${a.id_usuario}` },
        { titulo: "Acción", valor: (a) => legible(a.accion.includes(".") ? a.accion.split(".")[1] : a.accion) },
        { titulo: "Petición", valor: (a) => el("small", {}, `${a.metodo} ${a.ruta}`) },
        { titulo: "Resultado", valor: (a) => el("span", { class: a.exito ? "texto-si" : "texto-no" }, String(a.estado_http), a.error ? el("small", { class: "nota" }, ` ${a.error}`) : null) },
        { titulo: "Desde", valor: (a) => el("small", {}, a.ip) },
      ], datos.items, { vacio: "No hay actividad con estos filtros." }),
      paginacion({ pagina: datos.page, total: datos.total, tamano: datos.size, alCambiar: (n) => { filtros.page = n; cargar(); } }));
  }

  const cambio = (k) => (e) => { filtros[k] = e.target.value.trim(); filtros.page = 1; cargar(); };
  principal.replaceChildren(
    encabezado("Bitácora", "Registro automático de lo que hace cada usuario en el sistema. Se conserva 180 días."),
    el("div", { class: "filtros-barra" },
      campo("Usuario", selector("id_usuario", [["", "Todos"], ...usuarios.map((u) => [u.id_usuario, `${u.nombres} ${u.apellidos}`])], filtros.id_usuario, { onchange: cambio("id_usuario") })),
      campo("Acción", selector("accion", [["", "Todas"], ...[
        "INICIO_SESION", "VENTA_REGISTRADA", "PAGO_REGISTRADO", "FACTURA_EMITIDA", "PEDIDO_CAMBIO_ESTADO", "INVENTARIO_INGRESO",
        "INVENTARIO_AJUSTE", "TRASLADO_CREADO", "TRASLADO_DESPACHADO", "TRASLADO_RECIBIDO", "PRODUCTO_CREADO", "PRODUCTO_ACTUALIZADO",
        "FICHA_GUARDADA", "RESENA_MODERADA", "ESCANEO_QR"].map((a) => [a, legible(a)])], "", { onchange: cambio("accion") })),
      campo("Resultado", selector("exito", [["", "Todos"], ["true", "Correctos"], ["false", "Con error"]], "", { onchange: cambio("exito") })),
      campo("Desde", el("input", { type: "date", onchange: cambio("desde") })),
      campo("Hasta", el("input", { type: "date", onchange: cambio("hasta") }))),
    zona);
  await cargar();
}
