// Mostrador: venta en tienda (canal TIENDA). Se agregan prendas por código QR o
// por nombre, se identifica al cliente si quiere factura a su nombre y se cobra.
import { el, precio, qr, sinPrefijo } from "../comun.js";
import {
  aviso, buscadorVariantes, campo, datos, encabezado, errorEn, opcionesSedes, papi, selector,
} from "./ui.js";

export async function render(principal, ctx) {
  const { esAdmin, usuario, sedes } = ctx;
  const metodos = await papi("/metodos-pago");
  let lineas = [];
  let idSede = esAdmin ? sedes[0]?.id_sede : usuario.sede?.id_sede;

  const zonaLineas = el("div");
  const zonaError = el("div");
  const totalNodo = el("strong");

  const selectorSede = esAdmin
    ? campo("Sede de la venta", selector("id_sede", opcionesSedes(sedes), idSede, {
      onchange: (e) => { idSede = Number(e.target.value); lineas = []; pintar(); },
    }))
    : el("p", { class: "nota" }, `Venta en ${sinPrefijo(usuario.sede?.nombre)}`);

  function agregar(v) {
    const existente = lineas.find((l) => l.id_variante === v.id_variante);
    if (existente) existente.cantidad += 1; else lineas.push({ ...v, cantidad: 1 });
    pintar();
    aviso(`${v.descripcion} agregada.`);
  }

  function pintar() {
    totalNodo.textContent = precio(lineas.reduce((s, l) => s + l.precio * l.cantidad, 0));
    if (!lineas.length) {
      zonaLineas.replaceChildren(el("p", { class: "vacio" }, "Escanea o busca la primera prenda."));
      return;
    }
    zonaLineas.replaceChildren(el("ul", { class: "venta" }, lineas.map((l) => {
      const cantidad = el("input", { type: "number", min: 0, value: l.cantidad, "aria-label": `Cantidad de ${l.descripcion}` });
      cantidad.addEventListener("change", () => {
        l.cantidad = Math.max(0, Number(cantidad.value) || 0);
        lineas = lineas.filter((x) => x.cantidad > 0);
        pintar();
      });
      return el("li", {},
        el("div", {}, el("strong", {}, l.descripcion), el("span", { class: "nota" }, `${l.sku}, ${precio(l.precio)} c/u`)),
        cantidad,
        el("span", { class: "num" }, precio(l.precio * l.cantidad)));
    })));
  }

  const cliente = el("details", { class: "plegable" },
    el("summary", {}, "Factura a nombre del cliente (opcional)"),
    el("div", { class: "campos" },
      campo("Tipo de documento", selector("tipo_documento", [["CC", "Cédula"], ["CE", "Cédula de extranjería"], ["NIT", "NIT"], ["PASAPORTE", "Pasaporte"]], "CC")),
      campo("Número de documento", el("input", { name: "numero_documento", maxlength: 20, inputmode: "numeric" })),
      campo("Nombres", el("input", { name: "nombres", maxlength: 80 })),
      campo("Apellidos", el("input", { name: "apellidos", maxlength: 80 })),
      campo("Correo", el("input", { name: "email", type: "email", maxlength: 120 }), "Para enviar la factura electrónica."),
    ));

  const form = el("form", { class: "tarjeta cobro", novalidate: true },
    el("h2", {}, "Venta actual"),
    selectorSede,
    zonaLineas,
    el("p", { class: "cobro__total" }, el("span", {}, "Total"), totalNodo),
    cliente,
    campo("Medio de pago", selector("id_metodo_pago", metodos.map((m) => [m.id_metodo_pago, m.nombre]), metodos[0]?.id_metodo_pago)),
    zonaError,
    el("div", { class: "fila-botones" },
      el("button", { class: "boton boton--ancho", type: "submit" }, "Cobrar"),
      el("button", { class: "boton boton--secundario", type: "button", onclick: () => { lineas = []; form.reset(); zonaError.replaceChildren(); pintar(); } }, "Vaciar")));

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    zonaError.replaceChildren();
    if (!lineas.length) { errorEn(zonaError, new Error("Agrega al menos una prenda.")); return; }
    const f = Object.fromEntries(new FormData(form));
    const cuerpo = {
      canal: "TIENDA", tipo_entrega: "INMEDIATA",
      items: lineas.map((l) => ({ id_variante: l.id_variante, cantidad: l.cantidad })),
    };
    if (esAdmin) cuerpo.id_sede = idSede;
    if (f.numero_documento?.trim()) {
      if (!f.nombres?.trim()) { errorEn(zonaError, new Error("Para facturar a nombre del cliente escribe también sus nombres.")); return; }
      cuerpo.cliente = Object.fromEntries(["tipo_documento", "numero_documento", "nombres", "apellidos", "email"]
        .filter((k) => f[k]?.trim()).map((k) => [k, f[k].trim()]));
    }
    const boton = form.querySelector('button[type="submit"]');
    boton.disabled = true;
    boton.textContent = "Cobrando…";
    let pedido;
    try {
      pedido = await papi("/pedidos", { metodo: "POST", cuerpo });
      const pago = await papi(`/pedidos/${pedido.id_pedido}/pagos`, {
        metodo: "POST", cuerpo: { id_metodo_pago: Number(f.id_metodo_pago), monto: pedido.total },
      });
      recibo(pedido, pago);
    } catch (error) {
      errorEn(zonaError, pedido
        ? Object.assign(error, { message: `El pedido ${pedido.codigo_qr} quedó creado pero sin cobrar: ${error.message} Puedes cobrarlo desde Pedidos.` })
        : error);
      boton.disabled = false;
      boton.textContent = "Cobrar";
    }
  });

  function recibo(pedido, pago) {
    lineas = [];
    principal.replaceChildren(
      encabezado("Venta registrada", `${pedido.codigo_qr}, ${sinPrefijo(pedido.sede.nombre)}`,
        el("button", { class: "boton", type: "button", onclick: () => render(principal, ctx) }, "Nueva venta"),
        el("a", { class: "boton boton--secundario", href: `#/pedidos/${pedido.id_pedido}` }, "Ver el pedido")),
      el("div", { class: "rejilla-panel" },
        el("section", { class: "tarjeta" },
          el("h2", {}, "Detalle"),
          el("ul", { class: "venta" }, pedido.items.map((i) => el("li", {},
            el("div", {}, el("strong", {}, i.descripcion), el("span", { class: "nota" }, i.sku)),
            el("span", {}, `× ${i.cantidad}`), el("span", { class: "num" }, precio(i.subtotal_linea))))),
          datos([
            ["Subtotal", precio(pedido.subtotal)], ["IVA (19 %)", precio(pedido.impuestos)], ["Total", precio(pedido.total)],
            ["Medio de pago", pago.metodo_pago], ["Referencia", pago.referencia_transaccion],
          ])),
        el("section", { class: "tarjeta" },
          el("h2", {}, "Factura electrónica"),
          pago.factura
            ? datos([["Número", pago.factura.numero_factura], ["Estado DIAN", pago.factura.estado_dian], ["CUFE", pago.factura.cufe]])
            : el("p", {}, "La DIAN no respondió; la factura se puede emitir después desde el pedido."),
          el("div", { class: "confirmacion__qr" }, qr(pedido.codigo_qr, { tamano: 4 }), el("p", { class: "codigo-pedido" }, pedido.codigo_qr)))));
    aviso("Venta cobrada.");
  }

  principal.replaceChildren(
    encabezado("Mostrador", "Escanea la etiqueta de cada prenda o búscala por nombre."),
    el("div", { class: "mostrador" },
      el("section", { class: "tarjeta" },
        el("h2", {}, "Agregar prendas"),
        buscadorVariantes({ alElegir: agregar, sede: () => idSede })),
      form));
  pintar();
}
