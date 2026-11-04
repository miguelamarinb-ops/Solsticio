// Detalle de un pedido: prendas, cliente, envío, pagos y factura, con las
// acciones que permite su estado (cobrar, preparar, enviar, entregar, cancelar, facturar).
import { el, fechaHora, precio, qr, sinPrefijo } from "../comun.js";
import {
  aviso, campo, confirmar, datos, dialogo, encabezado, errorEn, insignia, legible, papi, selector, tabla,
} from "./ui.js";

// Mismas reglas que servicios/pedidos.py (la API vuelve a validarlas).
function siguientes(pedido) {
  const domicilio = pedido.tipo_entrega === "DOMICILIO";
  switch (pedido.estado) {
    case "PENDIENTE": return ["CANCELADO"];
    case "PAGADO": return domicilio ? ["PREPARANDO"] : ["PREPARANDO", "ENTREGADO"];
    case "PREPARANDO": return domicilio ? ["ENVIADO"] : ["ENTREGADO"];
    case "ENVIADO": return ["ENTREGADO"];
    default: return [];
  }
}
const VERBOS = { PREPARANDO: "Marcar en preparación", ENVIADO: "Marcar enviado", ENTREGADO: "Marcar entregado", CANCELADO: "Cancelar pedido" };

export async function render(principal, ctx, { id }) {
  const pedido = await papi(`/pedidos/${id}`);
  const zonaAcciones = el("div");

  async function cambiarEstado(estado) {
    let cuerpo = { estado };
    if (estado === "CANCELADO") {
      const ok = await confirmar("Cancelar pedido", `El pedido ${pedido.codigo_qr} se cancelará y se liberarán las prendas reservadas.`, { accion: "Cancelar pedido", peligro: true });
      if (!ok) return;
    }
    if (estado === "ENVIADO") {
      const transportadora = el("input", { name: "transportadora", maxlength: 60, value: "Servientrega" });
      const guia = el("input", { name: "numero_guia", maxlength: 60 });
      const ok = await new Promise((resolver) => {
        let aceptado = false;
        const d = dialogo({
          titulo: "Datos del envío",
          contenido: el("div", { class: "campos" }, campo("Transportadora", transportadora), campo("Número de guía", guia)),
          acciones: [
            el("button", { class: "boton boton--secundario", type: "button", onclick: () => d.close() }, "Cancelar"),
            el("button", { class: "boton", type: "button", onclick: () => { aceptado = true; d.close(); } }, "Marcar enviado")],
        });
        d.addEventListener("close", () => resolver(aceptado));
      });
      if (!ok) return;
      cuerpo = { ...cuerpo, transportadora: transportadora.value.trim(), numero_guia: guia.value.trim() };
    }
    try {
      await papi(`/pedidos/${pedido.id_pedido}/estado`, { metodo: "PATCH", cuerpo });
      aviso(`Pedido ${legible(estado).toLowerCase()}.`);
      render(principal, ctx, { id });
    } catch (error) { errorEn(zonaAcciones, error); }
  }

  async function cobrar() {
    const metodos = await papi("/metodos-pago");
    const metodo = selector("id_metodo_pago", metodos.map((m) => [m.id_metodo_pago, m.nombre]), metodos[0]?.id_metodo_pago);
    const d = dialogo({
      titulo: `Cobrar ${precio(pedido.total)}`,
      contenido: campo("Medio de pago", metodo),
      acciones: [
        el("button", { class: "boton boton--secundario", type: "button", onclick: () => d.close() }, "Cancelar"),
        el("button", { class: "boton", type: "button", onclick: async () => {
          d.close();
          try {
            await papi(`/pedidos/${pedido.id_pedido}/pagos`, { metodo: "POST", cuerpo: { id_metodo_pago: Number(metodo.value), monto: pedido.total } });
            aviso("Pago registrado.");
            render(principal, ctx, { id });
          } catch (error) { errorEn(zonaAcciones, error); }
        } }, "Registrar pago")],
    });
  }

  async function facturar() {
    try {
      await papi(`/pedidos/${pedido.id_pedido}/factura`, { metodo: "POST" });
      aviso("Factura emitida y validada por la DIAN.");
      render(principal, ctx, { id });
    } catch (error) { errorEn(zonaAcciones, error); }
  }

  const pagado = pedido.pagos.some((p) => p.estado === "APROBADO");
  const facturable = pagado && (!pedido.factura || pedido.factura.estado_dian !== "VALIDADA");
  const acciones = [
    pedido.estado === "PENDIENTE" ? el("button", { class: "boton", type: "button", onclick: cobrar }, "Cobrar") : null,
    ...siguientes(pedido).filter((e) => e !== "CANCELADO").map((e) =>
      el("button", { class: "boton", type: "button", onclick: () => cambiarEstado(e) }, VERBOS[e])),
    facturable ? el("button", { class: "boton boton--secundario", type: "button", onclick: facturar }, pedido.factura ? "Reintentar factura" : "Emitir factura") : null,
    siguientes(pedido).includes("CANCELADO") ? el("button", { class: "boton boton--peligro-texto", type: "button", onclick: () => cambiarEstado("CANCELADO") }, "Cancelar pedido") : null,
  ].filter(Boolean);

  const c = pedido.cliente;
  principal.replaceChildren(
    el("p", { class: "migas" }, el("a", { href: "#/pedidos" }, "Pedidos"), ` / ${pedido.codigo_qr}`),
    encabezado(`Pedido ${pedido.codigo_qr}`, `${legible(pedido.canal)}, ${sinPrefijo(pedido.sede.nombre)}, ${fechaHora(pedido.fecha_pedido)}`),
    el("div", { class: "estado-pedido" }, insignia(pedido.estado), el("span", {}, legible(pedido.tipo_entrega))),
    acciones.length ? el("div", { class: "pagina__acciones pagina__acciones--bloque" }, acciones) : "",
    zonaAcciones,
    el("div", { class: "rejilla-panel rejilla-panel--detalle" },
      el("section", { class: "tarjeta" },
        el("h2", {}, "Prendas"),
        tabla([
          { titulo: "Prenda", valor: (i) => el("span", {}, i.descripcion, el("br"), el("small", { class: "nota" }, i.sku)) },
          { titulo: "Cant.", valor: (i) => String(i.cantidad), clase: "num" },
          { titulo: "Precio", valor: (i) => precio(i.precio_unitario), clase: "num" },
          { titulo: "Subtotal", valor: (i) => precio(i.subtotal_linea), clase: "num" },
        ], pedido.items),
        datos([["Subtotal", precio(pedido.subtotal)], ["IVA (19 %)", precio(pedido.impuestos)], ["Total", el("strong", {}, precio(pedido.total))]])),
      el("div", { class: "pila" },
        el("section", { class: "tarjeta tarjeta--qr" }, qr(pedido.codigo_qr, { tamano: 3 }),
          el("p", { class: "nota" }, "El cliente muestra este código para recoger.")),
        el("section", { class: "tarjeta" },
          el("h2", {}, "Cliente"),
          c ? datos([["Nombre", `${c.nombres} ${c.apellidos || ""}`], ["Documento", `${c.tipo_documento} ${c.numero_documento}`], ["Correo", c.email], ["Teléfono", c.telefono]])
            : el("p", { class: "nota" }, "Venta sin cliente identificado."),
          pedido.vendido_por ? el("p", { class: "nota" }, `Vendido por ${pedido.vendido_por}.`) : null),
        pedido.envio ? el("section", { class: "tarjeta" },
          el("h2", {}, "Envío"),
          datos([["Dirección", `${pedido.envio.direccion}, ${pedido.envio.ciudad}`], ["Recibe", pedido.envio.destinatario],
            ["Teléfono", pedido.envio.telefono_contacto], ["Estado", legible(pedido.envio.estado)],
            ["Transportadora", pedido.envio.transportadora], ["Guía", pedido.envio.numero_guia],
            ["Despachado", fechaHora(pedido.envio.fecha_despacho)], ["Entregado", fechaHora(pedido.envio.fecha_entrega)]])) : null,
        el("section", { class: "tarjeta" },
          el("h2", {}, "Pagos"),
          tabla([
            { titulo: "Medio", valor: (p) => p.metodo_pago },
            { titulo: "Monto", valor: (p) => precio(p.monto), clase: "num" },
            { titulo: "Estado", valor: (p) => insignia(p.estado) },
            { titulo: "Referencia", valor: (p) => el("small", {}, p.referencia_transaccion) },
          ], pedido.pagos, { vacio: "Sin pagos registrados." })),
        el("section", { class: "tarjeta" },
          el("h2", {}, "Factura electrónica"),
          pedido.factura
            ? datos([["Número", pedido.factura.numero_factura], ["Estado DIAN", insignia(pedido.factura.estado_dian)],
              ["Emitida", fechaHora(pedido.factura.fecha_emision)], ["CUFE", el("small", { class: "cufe" }, pedido.factura.cufe)]])
            : el("p", { class: "nota" }, pagado ? "Aún no se ha emitido." : "Se emite cuando el pedido se paga.")))),
  );
}
