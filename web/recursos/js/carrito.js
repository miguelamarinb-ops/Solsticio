// Carrito y pago. El pedido web sale de una sola sede (la elegida en la cabecera):
// POST /pedidos con canal WEB y luego POST /pedidos/{id}/pagos con la pasarela
// simulada. Si el pago se aprueba la API emite la factura sola.
import {
  api, carrito, el, foto, iniciarCabecera, marcarInvalidos, mostrarError, precio, qr,
} from "./comun.js";

const raiz = document.getElementById("carrito");
let cabecera;
let metodos = [];

// ---------------------------------------------------------------------
// Lista del carrito
// ---------------------------------------------------------------------
function filaItem(item) {
  const cantidad = el("input", {
    type: "number", min: 0, max: 99, value: item.cantidad, inputmode: "numeric",
    "aria-label": `Cantidad de ${item.nombre}, talla ${item.talla}`,
  });
  cantidad.addEventListener("change", () => {
    carrito.cambiar(item.id_variante, Math.max(0, Math.min(99, Number(cantidad.value) || 0)));
    pintarCarrito();
  });
  return el("li", { class: "linea" },
    el("a", { class: "linea__foto", href: `/producto?id=${item.id_producto}`, tabindex: "-1", "aria-hidden": "true" },
      foto(item.imagen, item.nombre)),
    el("div", { class: "linea__datos" },
      el("a", { href: `/producto?id=${item.id_producto}`, class: "linea__nombre" }, item.nombre),
      el("p", {}, `Talla ${item.talla}, ${item.color}`),
      el("p", { class: "linea__unitario" }, `${precio(item.precio)} c/u`)),
    el("label", { class: "linea__cantidad" }, el("span", { class: "solo-lector" }, "Cantidad"), cantidad),
    el("p", { class: "linea__total" }, precio(item.precio * item.cantidad)),
    el("button", {
      class: "linea__quitar", type: "button", "aria-label": `Quitar ${item.nombre} del carrito`,
      onclick: () => { carrito.cambiar(item.id_variante, 0); pintarCarrito(); },
    }, "Quitar"),
  );
}

function pintarCarrito(error) {
  const items = carrito.items();
  if (!items.length) {
    raiz.replaceChildren(
      el("h1", { class: "titulo-pagina" }, "Tu carrito"),
      el("div", { class: "aviso" }, el("p", {}, "Todavía no has agregado prendas."),
        el("p", {}, el("a", { class: "boton", href: "/" }, "Ver el catálogo"))));
    return;
  }
  raiz.replaceChildren(
    el("h1", { class: "titulo-pagina" }, "Tu carrito"),
    el("p", { class: "subtitulo" }, `Tu pedido sale de la sede ${cabecera.nombreSede()}. Puedes recogerlo allí o pedir envío a domicilio.`),
    el("div", { class: "pago" },
      el("section", { "aria-label": "Prendas" },
        el("ul", { class: "lineas" }, items.map(filaItem)),
        el("div", { class: "totales" },
          el("p", {}, el("span", {}, "Total con IVA incluido"), el("strong", {}, precio(carrito.total()))))),
      formularioPago(error)),
  );
}

// ---------------------------------------------------------------------
// Formulario de pago
// ---------------------------------------------------------------------
function campo(texto, atributos, ayuda) {
  const control = el("input", atributos);
  return el("div", { class: "campo" }, el("label", { for: atributos.id }, texto), control,
    ayuda ? el("small", {}, ayuda) : null);
}

function formularioPago(error) {
  const zonaEnvio = el("div", { class: "campos", id: "zona-envio", hidden: true },
    campo("Dirección", { id: "env-direccion", name: "direccion", maxlength: 150, autocomplete: "street-address" }),
    campo("Ciudad", { id: "env-ciudad", name: "ciudad", maxlength: 60, value: "Bogotá", autocomplete: "address-level2" }),
    campo("Quién recibe", { id: "env-destinatario", name: "destinatario", maxlength: 120, autocomplete: "name" }),
    campo("Teléfono de contacto", { id: "env-telefono", name: "telefono_contacto", maxlength: 20, type: "tel", autocomplete: "tel" }),
  );

  const mensaje = el("div", { role: "alert" });
  if (error) mostrarError(mensaje, error);

  const form = el("form", { class: "formulario formulario--pago", novalidate: true },
    el("h2", {}, "Tus datos"),
    el("div", { class: "campos" },
      el("div", { class: "campo" }, el("label", { for: "cli-tipo" }, "Tipo de documento"),
        el("select", { id: "cli-tipo", name: "tipo_documento" },
          el("option", { value: "CC" }, "Cédula de ciudadanía"), el("option", { value: "CE" }, "Cédula de extranjería"),
          el("option", { value: "PASAPORTE" }, "Pasaporte"), el("option", { value: "NIT" }, "NIT"))),
      campo("Número de documento", { id: "cli-numero", name: "numero_documento", maxlength: 20, required: true, inputmode: "numeric" }),
      campo("Nombres", { id: "cli-nombres", name: "nombres", maxlength: 80, required: true, autocomplete: "given-name" }),
      campo("Apellidos (opcional)", { id: "cli-apellidos", name: "apellidos", maxlength: 80, autocomplete: "family-name" }),
      campo("Correo", { id: "cli-email", name: "email", type: "email", maxlength: 120, required: true, autocomplete: "email" },
        "Te enviamos aquí la factura electrónica."),
      campo("Celular (opcional)", { id: "cli-telefono", name: "telefono", type: "tel", maxlength: 20, autocomplete: "tel" }),
    ),
    el("fieldset", { class: "opciones" },
      el("legend", {}, "Entrega"),
      el("div", { class: "opciones__lista" },
        el("label", { class: "opcion" }, el("input", { type: "radio", name: "tipo_entrega", value: "RECOGER_EN_TIENDA", checked: true }),
          el("span", {}, `Recoger en ${cabecera.nombreSede()}`)),
        el("label", { class: "opcion" }, el("input", { type: "radio", name: "tipo_entrega", value: "DOMICILIO" }),
          el("span", {}, "Envío a domicilio")))),
    zonaEnvio,
    el("fieldset", { class: "opciones" },
      el("legend", {}, "Medio de pago"),
      el("div", { class: "opciones__lista" }, metodos.filter((m) => m.tipo !== "EFECTIVO").map((m, i) =>
        el("label", { class: "opcion" }, el("input", { type: "radio", name: "id_metodo_pago", value: m.id_metodo_pago, checked: i === 0 }),
          el("span", {}, m.nombre))))),
    el("p", { class: "nota-compra" }, "Pago de prueba: la pasarela es simulada y no se cobra dinero real."),
    el("label", { class: "casilla" }, el("input", { type: "checkbox", name: "simular_rechazo" }),
      " Simular un pago rechazado (para la demostración)"),
    mensaje,
    el("button", { class: "boton boton--compra boton--ancho", type: "submit" }, `Pagar ${precio(carrito.total())}`),
  );

  form.addEventListener("change", (evento) => {
    if (evento.target.name === "tipo_entrega") zonaEnvio.hidden = evento.target.value !== "DOMICILIO";
  });
  form.addEventListener("submit", (evento) => pagar(evento, form, mensaje));
  return form;
}

// Devuelve [nombre del campo, texto para el mensaje] de cada dato que falta.
function validar(datos) {
  const faltan = [];
  if (!datos.numero_documento?.trim()) faltan.push(["numero_documento", "el número de documento"]);
  if (!datos.nombres?.trim()) faltan.push(["nombres", "tus nombres"]);
  if (!datos.email?.includes("@")) faltan.push(["email", "un correo válido"]);
  if (datos.tipo_entrega === "DOMICILIO") {
    for (const [clave, texto] of [["direccion", "la dirección"], ["ciudad", "la ciudad"], ["destinatario", "quién recibe"], ["telefono_contacto", "el teléfono de contacto"]]) {
      if (!datos[clave]?.trim()) faltan.push([clave, texto]);
    }
  }
  return faltan;
}

async function pagar(evento, form, mensaje) {
  evento.preventDefault();
  const datos = Object.fromEntries(new FormData(form));
  const faltan = validar(datos);
  if (faltan.length) {
    mensaje.replaceChildren(el("div", { class: "aviso aviso--error" }, el("p", {}, `Falta ${faltan.map(([, t]) => t).join(", ")}.`)));
    marcarInvalidos(form, faltan.map(([n]) => n));
    return;
  }
  const boton = form.querySelector('button[type="submit"]');
  boton.disabled = true;
  boton.textContent = "Procesando pago…";

  const cuerpo = {
    canal: "WEB", id_sede: cabecera.sedeActual(), tipo_entrega: datos.tipo_entrega,
    cliente: Object.fromEntries(["tipo_documento", "numero_documento", "nombres", "apellidos", "email", "telefono"]
      .filter((k) => datos[k]?.trim()).map((k) => [k, datos[k].trim()])),
    items: carrito.items().map((i) => ({ id_variante: i.id_variante, cantidad: i.cantidad })),
  };
  if (datos.tipo_entrega === "DOMICILIO") {
    cuerpo.envio = Object.fromEntries(["direccion", "ciudad", "destinatario", "telefono_contacto"].map((k) => [k, datos[k].trim()]));
  }

  let pedido;
  try {
    pedido = await api("/pedidos", { metodo: "POST", cuerpo });
  } catch (error) {
    boton.disabled = false;
    boton.textContent = `Pagar ${precio(carrito.total())}`;
    if (error.estado === 409) error.message = `Algunas prendas ya no alcanzan en ${cabecera.nombreSede()}. Ajusta las cantidades o cambia de sede.`;
    mostrarError(mensaje, error);
    return;
  }

  try {
    const pago = await api(`/pedidos/${pedido.id_pedido}/pagos`, {
      metodo: "POST",
      cuerpo: { id_metodo_pago: Number(datos.id_metodo_pago), monto: pedido.total, simular_rechazo: datos.simular_rechazo === "on" },
    });
    carrito.vaciar();
    confirmar(pedido, pago);
  } catch (error) {
    if (error.estado === 402) {
      rechazado(pedido, error.cuerpo);
    } else {
      boton.disabled = false;
      mostrarError(mensaje, error);
    }
  }
}

// ---------------------------------------------------------------------
// Resultado
// ---------------------------------------------------------------------
function resumenPedido(pedido) {
  return el("ul", { class: "lineas lineas--compactas" }, pedido.items.map((i) =>
    el("li", { class: "linea linea--compacta" },
      el("span", {}, `${i.cantidad} × ${i.descripcion}`), el("span", {}, precio(i.subtotal_linea)))));
}

function confirmar(pedido, pago) {
  const recoger = pedido.tipo_entrega === "RECOGER_EN_TIENDA";
  window.scrollTo({ top: 0 });
  raiz.replaceChildren(el("section", { class: "confirmacion", "aria-labelledby": "titulo-confirmacion" },
    el("div", { class: "confirmacion__ticket" },
      el("p", { class: "detalle__categoria" }, "Pedido pagado"),
      el("h1", { class: "titulo-pagina", id: "titulo-confirmacion", tabindex: "-1" }, `Gracias, ${pedido.cliente.nombres}`),
      el("p", {}, recoger
        ? `Recoge tu pedido en ${pedido.sede.nombre} mostrando este código.`
        : `Preparamos tu envío a ${pedido.envio.direccion}, ${pedido.envio.ciudad}.`),
      el("div", { class: "confirmacion__qr" }, qr(pedido.codigo_qr, { tamano: 5 }), el("p", { class: "codigo-pedido" }, pedido.codigo_qr)),
      resumenPedido(pedido),
      el("dl", { class: "datos" },
        el("dt", {}, "Total pagado"), el("dd", {}, precio(pedido.total)),
        el("dt", {}, "Medio de pago"), el("dd", {}, pago.metodo_pago),
        el("dt", {}, "Referencia"), el("dd", {}, pago.referencia_transaccion),
        pago.factura ? [el("dt", {}, "Factura electrónica"), el("dd", {}, `${pago.factura.numero_factura} (${pago.factura.estado_dian === "VALIDADA" ? "validada por la DIAN" : "en validación"})`)] : null),
      el("p", {}, el("a", { class: "boton boton--secundario", href: "/" }, "Seguir comprando"))),
  ));
  document.getElementById("titulo-confirmacion").focus();
}

function rechazado(pedido, cuerpo) {
  raiz.replaceChildren(el("section", { class: "confirmacion" },
    el("div", { class: "confirmacion__ticket" },
      el("p", { class: "detalle__categoria texto-no" }, "Pago rechazado"),
      el("h1", { class: "titulo-pagina", tabindex: "-1", id: "titulo-rechazo" }, "Tu banco no aprobó el pago"),
      el("p", {}, `El pedido ${pedido.codigo_qr} quedó sin pagar y liberamos las prendas. Tus prendas siguen en el carrito para que lo intentes con otro medio.`),
      el("p", { class: "nota-compra" }, `Referencia de la transacción: ${cuerpo.referencia_transaccion}`),
      el("p", {}, el("button", { class: "boton", type: "button", onclick: () => pintarCarrito() }, "Intentar de nuevo")))));
  document.getElementById("titulo-rechazo").focus();
}

async function iniciar() {
  try {
    cabecera = await iniciarCabecera({ alCambiarSede: () => pintarCarrito() });
    metodos = await api("/metodos-pago");
    pintarCarrito();
  } catch (error) {
    mostrarError(raiz, error, iniciar);
  }
}

iniciar();
