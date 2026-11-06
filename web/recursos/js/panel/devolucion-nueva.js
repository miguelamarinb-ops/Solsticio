// Registrar una devolución o un cambio: se busca el pedido por el código de su
// comprobante, se eligen las prendas y cantidades, y al guardar la API reintegra
// el stock en esta sede, entrega la prenda de cambio y emite la nota crédito.
import { el, precio, sinPrefijo } from "../comun.js";
import { aviso, campo, encabezado, errorEn, insignia, opcionesSedes, papi, selector } from "./ui.js";

export async function render(principal, ctx) {
  const codigo = ctx.consulta().get("codigo") || "";
  const migas = el("p", { class: "migas" }, el("a", { href: "#/devoluciones" }, "Devoluciones"), " / Registrar");
  if (!codigo) { ctx.navegar("#/devoluciones"); return; }

  let pedido;
  try {
    pedido = await papi(`/devoluciones/pedido?codigo=${encodeURIComponent(codigo)}`);
  } catch (error) {
    const zona = el("div");
    principal.replaceChildren(migas, encabezado("Registrar devolución"), zona);
    errorEn(zona, error.estado === 404 ? new Error(`No existe un pedido con el código ${codigo}.`) : error);
    return;
  }

  // Tallas y colores de cada prenda del pedido, para el cambio.
  const productos = {};
  await Promise.all([...new Set(pedido.items.map((i) => i.id_producto))].map(async (id) => {
    productos[id] = await papi(`/productos/${id}`);
  }));

  const mensaje = el("div", { role: "alert" });
  const sedeSelect = ctx.esAdmin
    ? selector("id_sede", opcionesSedes(ctx.sedes), pedido.sede.id_sede)
    : null;
  const sedeRecibe = () => (ctx.esAdmin ? Number(sedeSelect.value) : ctx.usuario.sede.id_sede);
  const tipoSelect = selector("tipo", [["DEVOLUCION", "Devolución (se reembolsa)"], ["CAMBIO", "Cambio de talla o color"]], "DEVOLUCION");
  const motivo = el("input", { name: "motivo", maxlength: 200, required: true, placeholder: "Ej. la talla M le queda ajustada" });

  const filas = pedido.items.map((item) => {
    const cantidad = el("input", { type: "number", min: 0, max: item.devolvible, value: item.devolvible ? 1 : 0, inputmode: "numeric",
      disabled: !item.devolvible, "aria-label": `Unidades a devolver de ${item.descripcion}` });
    const opciones = (productos[item.id_producto]?.variantes || [])
      .filter((v) => v.id_variante !== item.id_variante && v.precio_final <= item.precio_unitario)
      .map((v) => {
        const hay = v.disponibilidad.find((d) => d.id_sede === sedeRecibe())?.cantidad ?? 0;
        return [v.id_variante, `${v.talla} - ${v.color.nombre} (${hay} en esta sede)`];
      });
    const cambio = selector("id_variante_cambio", [["", "Elige la prenda que se lleva"], ...opciones], "",
      { "aria-label": `Prenda de cambio para ${item.descripcion}` });
    const celdaCambio = el("td", { "data-titulo": "Se lleva a cambio" }, opciones.length ? cambio : el("small", { class: "nota" }, "No hay otra talla o color"));
    return { item, cantidad, cambio, celdaCambio };
  });

  function mostrarCambio() {
    const esCambio = tipoSelect.value === "CAMBIO";
    for (const f of filas) f.celdaCambio.hidden = !esCambio;
    columnaCambio.hidden = !esCambio;
  }
  const columnaCambio = el("th", { scope: "col" }, "Se lleva a cambio");
  tipoSelect.addEventListener("change", mostrarCambio);

  const tablaItems = el("div", { class: "tabla-caja" }, el("table", { class: "tabla" },
    el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Prenda"), el("th", { scope: "col", class: "num" }, "Comprado"),
      el("th", { scope: "col", class: "num" }, "Se puede devolver"), el("th", { scope: "col", class: "num" }, "Precio"),
      el("th", { scope: "col" }, "Devuelve"), columnaCambio)),
    el("tbody", {}, filas.map(({ item, cantidad, celdaCambio }) => el("tr", {},
      el("td", { "data-titulo": "Prenda" }, item.descripcion, el("br"), el("small", { class: "nota" }, item.sku)),
      el("td", { class: "num", "data-titulo": "Comprado" }, String(item.cantidad)),
      el("td", { class: "num", "data-titulo": "Se puede devolver" }, String(item.devolvible)),
      el("td", { class: "num", "data-titulo": "Precio" }, precio(item.precio_unitario)),
      el("td", { "data-titulo": "Devuelve" }, cantidad),
      celdaCambio)))));
  mostrarCambio();

  const boton = el("button", { class: "boton", type: "submit" }, "Registrar y emitir nota crédito");
  const form = el("form", { class: "tarjeta", novalidate: true },
    el("div", { class: "campos" },
      campo("Tipo", tipoSelect),
      sedeSelect ? campo("Sede que recibe", sedeSelect, "El stock vuelve a esta sede.") : null,
      campo("Motivo", motivo, null, { ancho: true })),
    el("h2", {}, "Prendas"),
    tablaItems,
    mensaje,
    el("div", { class: "pagina__acciones" }, boton));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    mensaje.replaceChildren();
    const tipo = tipoSelect.value;
    const items = filas.filter((f) => Number(f.cantidad.value) > 0).map((f) => ({
      id_detalle_pedido: f.item.id_detalle_pedido, cantidad: Number(f.cantidad.value),
      ...(tipo === "CAMBIO" ? { id_variante_cambio: Number(f.cambio.value) || null } : {}),
    }));
    const faltan = [];
    if (!motivo.value.trim()) faltan.push("el motivo");
    if (!items.length) faltan.push("al menos una prenda");
    if (tipo === "CAMBIO" && items.some((i) => !i.id_variante_cambio)) faltan.push("la prenda de cambio");
    if (faltan.length) { errorEn(mensaje, new Error(`Falta ${faltan.join(", ")}.`)); return; }
    boton.disabled = true;
    try {
      const dev = await papi("/devoluciones", { metodo: "POST", cuerpo: {
        id_pedido: pedido.id_pedido, id_sede: sedeRecibe(), tipo, motivo: motivo.value.trim(), items } });
      aviso(`Devolución registrada. Nota crédito ${dev.nota_credito.numero_nota} por ${precio(dev.nota_credito.monto)}.`);
      ctx.navegar(`#/devoluciones/${dev.id_devolucion}`);
    } catch (error) {
      boton.disabled = false;
      errorEn(mensaje, error);
    }
  });

  const c = pedido.cliente;
  const nadaQueDevolver = pedido.items.every((i) => !i.devolvible);
  principal.replaceChildren(
    migas,
    encabezado(`Devolución del pedido ${pedido.codigo_qr}`,
      `${c ? `${c.nombres} ${c.apellidos || ""}, ` : ""}vendido en ${sinPrefijo(pedido.sede.nombre)}. ` +
      (ctx.esAdmin ? "" : `Se recibe en ${sinPrefijo(ctx.usuario.sede.nombre)}.`)),
    el("div", { class: "estado-pedido" }, insignia(pedido.estado), el("span", {}, `Total ${precio(pedido.total)}`)),
    nadaQueDevolver
      ? el("div", { class: "aviso" }, el("p", {}, "Todas las prendas de este pedido ya se devolvieron o el pedido no está pagado."))
      : form,
    pedido.devoluciones.length ? el("section", { class: "tarjeta" }, el("h2", {}, "Devoluciones anteriores de este pedido"),
      el("ul", {}, pedido.devoluciones.map((d) => el("li", {},
        el("a", { href: `#/devoluciones/${d.id_devolucion}` }, `#${d.id_devolucion}`), " ", insignia(d.tipo), " ", insignia(d.estado))))) : null,
  );
}
