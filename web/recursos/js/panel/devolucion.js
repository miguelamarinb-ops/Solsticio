// Detalle de una devolución o cambio: prendas devueltas y entregadas, movimientos de
// inventario que generó y nota crédito. Una solicitud del cliente se completa (cuando
// la prenda llega a la sede) o se rechaza.
import { el, fechaHora, precio, sinPrefijo } from "../comun.js";
import { aviso, confirmar, datos, encabezado, errorEn, insignia, legible, papi, tabla } from "./ui.js";

export async function render(principal, ctx, { id }) {
  const dev = await papi(`/devoluciones/${id}`);
  const zonaAcciones = el("div");

  async function procesar(accion) {
    const textos = accion === "COMPLETAR"
      ? ["Recibir prendas", `Las prendas entran al inventario de ${sinPrefijo(dev.sede.nombre)} y se emite la nota crédito.`, "Recibir y emitir nota"]
      : ["Rechazar solicitud", "El cliente verá la solicitud como rechazada y las unidades vuelven a poder devolverse.", "Rechazar"];
    if (!await confirmar(textos[0], textos[1], { accion: textos[2], peligro: accion === "RECHAZAR" })) return;
    try {
      await papi(`/devoluciones/${dev.id_devolucion}`, { metodo: "PATCH", cuerpo: { accion } });
      aviso(accion === "COMPLETAR" ? "Devolución completada." : "Solicitud rechazada.");
      render(principal, ctx, { id });
    } catch (error) { errorEn(zonaAcciones, error); }
  }

  const pendiente = dev.estado === "SOLICITADA";
  const c = dev.cliente;
  const nota = dev.nota_credito;
  principal.replaceChildren(
    el("p", { class: "migas" }, el("a", { href: "#/devoluciones" }, "Devoluciones"), ` / #${dev.id_devolucion}`),
    encabezado(`${legible(dev.tipo)} #${dev.id_devolucion}`,
      `Pedido ${dev.codigo_pedido}, ${sinPrefijo(dev.sede.nombre)}, ${fechaHora(dev.fecha_solicitud)}`),
    el("div", { class: "estado-pedido" }, insignia(dev.estado), insignia(dev.tipo)),
    pendiente ? el("div", { class: "pagina__acciones pagina__acciones--bloque" },
      el("button", { class: "boton", type: "button", onclick: () => procesar("COMPLETAR") }, "Recibir prendas y emitir nota"),
      el("button", { class: "boton boton--peligro-texto", type: "button", onclick: () => procesar("RECHAZAR") }, "Rechazar solicitud")) : "",
    zonaAcciones,
    el("div", { class: "rejilla-panel rejilla-panel--detalle" },
      el("div", { class: "pila" },
        el("section", { class: "tarjeta" },
          el("h2", {}, "Prendas"),
          tabla([
            { titulo: "Devuelve", valor: (i) => el("span", {}, i.devuelto.descripcion, el("br"), el("small", { class: "nota" }, i.devuelto.sku)) },
            { titulo: "Cant.", valor: (i) => String(i.devuelto.cantidad), clase: "num" },
            { titulo: "Precio pagado", valor: (i) => precio(i.devuelto.precio_unitario), clase: "num" },
            { titulo: "Se lleva", valor: (i) => (i.entregado ? el("span", {}, i.entregado.descripcion, el("br"), el("small", { class: "nota" }, i.entregado.sku)) : "—") },
          ], dev.items),
          datos([["Motivo", dev.motivo]])),
        el("section", { class: "tarjeta" },
          el("h2", {}, "Movimientos de inventario"),
          tabla([
            { titulo: "N.º", valor: (m) => `#${m.id_movimiento}` },
            { titulo: "Tipo", valor: (m) => insignia(m.tipo) },
            { titulo: "Variante", valor: (m) => String(m.id_variante) },
            { titulo: "Cantidad", valor: (m) => (m.cantidad > 0 ? `+${m.cantidad}` : String(m.cantidad)), clase: "num" },
          ], dev.movimientos_generados, { vacio: pendiente ? "Se generan cuando la sede recibe las prendas." : "Sin movimientos." }))),
      el("div", { class: "pila" },
        el("section", { class: "tarjeta" },
          el("h2", {}, "Nota crédito"),
          nota ? datos([["Número", nota.numero_nota], ["Monto", el("strong", {}, precio(nota.monto))],
            ["Estado DIAN", insignia(nota.estado_dian)], ["Emitida", fechaHora(nota.fecha_emision)],
            ["CUDE", el("small", { class: "cufe" }, nota.cude)]])
            : el("p", { class: "nota" }, pendiente ? "Se emite al recibir las prendas." : "No se emitió.")),
        el("section", { class: "tarjeta" },
          el("h2", {}, "Cliente"),
          c ? datos([["Nombre", `${c.nombres} ${c.apellidos || ""}`], ["Documento", `${c.tipo_documento} ${c.numero_documento}`], ["Correo", c.email]])
            : el("p", { class: "nota" }, "Venta sin cliente identificado."),
          el("p", { class: "nota" }, pendiente ? `Solicitada por ${dev.gestionado_por}.` : `Gestionada por ${dev.gestionado_por}.`)))),
  );
}
