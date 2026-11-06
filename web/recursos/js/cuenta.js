// Cuenta del cliente (rol CLIENTE): crear cuenta, iniciar sesión y ver mis pedidos.
// POST /auth/registro y POST /auth/login devuelven el token JWT; con él se piden
// GET /auth/perfil y GET /cuenta/pedidos (rutas que solo acepta el rol CLIENTE).
import {
  api, el, fecha, iniciarCabecera, marcarInvalidos, mostrarError, precio, qr, sesionCliente,
} from "./comun.js";

const raiz = document.getElementById("cuenta");

const ESTADOS = {
  PENDIENTE: "Pendiente de pago",
  PAGADO: "Pagado",
  PREPARANDO: "En preparación",
  ENVIADO: "Enviado",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
};

const ENTREGAS = {
  RECOGER_EN_TIENDA: "Recoger en tienda",
  DOMICILIO: "Envío a domicilio",
  INMEDIATA: "Compra en tienda",
};

function campo(texto, atributos, ayuda) {
  return el("div", { class: "campo" }, el("label", { for: atributos.id }, texto), el("input", atributos),
    ayuda ? el("small", {}, ayuda) : null);
}

// Llamada con el token del cliente. Si el token venció, se cierra la sesión.
async function capi(ruta, opciones = {}) {
  try {
    return await api(ruta, { ...opciones, token: sesionCliente.leer()?.token });
  } catch (error) {
    if (error.estado === 401) {
      sesionCliente.cerrar();
      pantallaAcceso("entrar", "Tu sesión terminó. Vuelve a iniciar sesión.");
    }
    throw error;
  }
}

// ---------------------------------------------------------------------
// Entrar / crear cuenta
// ---------------------------------------------------------------------
function formularioEntrar(mensaje) {
  const error = el("div", { role: "alert" });
  if (mensaje) error.append(el("div", { class: "aviso" }, el("p", {}, mensaje)));
  const form = el("form", { class: "formulario", novalidate: true, "aria-labelledby": "titulo-entrar" },
    el("h2", { id: "titulo-entrar" }, "Entrar"),
    el("div", { class: "campos" },
      campo("Correo", { id: "ent-email", name: "email", type: "email", autocomplete: "username", required: true }),
      campo("Contraseña", { id: "ent-clave", name: "password", type: "password", autocomplete: "current-password", required: true })),
    error,
    el("button", { class: "boton boton--ancho", type: "submit" }, "Entrar"));

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const datos = Object.fromEntries(new FormData(form));
    if (!datos.email || !datos.password) {
      error.replaceChildren(el("div", { class: "aviso aviso--error" }, el("p", {}, "Escribe tu correo y tu contraseña.")));
      marcarInvalidos(form, ["email", "password"].filter((k) => !datos[k]));
      return;
    }
    const boton = form.querySelector("button");
    boton.disabled = true;
    try {
      const r = await api("/auth/login", { metodo: "POST", cuerpo: datos });
      if (r.usuario.rol !== "CLIENTE") {
        error.replaceChildren(el("div", { class: "aviso" }, el("p", {}, "Esa es una cuenta del personal. ",
          el("a", { href: "/panel" }, "Entra por el panel"), ".")));
        boton.disabled = false;
        return;
      }
      sesionCliente.guardar(r.access_token, r.usuario, r.expira_en);
      location.reload();
    } catch (e) {
      if (e.estado === 401) e.message = "El correo o la contraseña no coinciden.";
      mostrarError(error, e);
      boton.disabled = false;
    }
  });
  return form;
}

function formularioRegistro() {
  const error = el("div", { role: "alert" });
  const form = el("form", { class: "formulario", novalidate: true, "aria-labelledby": "titulo-registro" },
    el("h2", { id: "titulo-registro" }, "Crear cuenta"),
    el("p", { class: "subtitulo" }, "Con tu cuenta compras sin volver a escribir tus datos y sigues el estado de tus pedidos."),
    el("div", { class: "campos" },
      el("div", { class: "campo" }, el("label", { for: "reg-tipo" }, "Tipo de documento"),
        el("select", { id: "reg-tipo", name: "tipo_documento" },
          el("option", { value: "CC" }, "Cédula de ciudadanía"), el("option", { value: "CE" }, "Cédula de extranjería"),
          el("option", { value: "PASAPORTE" }, "Pasaporte"))),
      campo("Número de documento", { id: "reg-documento", name: "documento", maxlength: 20, required: true, inputmode: "numeric" }),
      campo("Nombres", { id: "reg-nombres", name: "nombres", maxlength: 80, required: true, autocomplete: "given-name" }),
      campo("Apellidos", { id: "reg-apellidos", name: "apellidos", maxlength: 80, required: true, autocomplete: "family-name" }),
      campo("Correo", { id: "reg-email", name: "email", type: "email", maxlength: 120, required: true, autocomplete: "email" }),
      campo("Celular (opcional)", { id: "reg-telefono", name: "telefono", type: "tel", maxlength: 20, autocomplete: "tel" }),
      campo("Contraseña", { id: "reg-clave", name: "password", type: "password", minlength: 8, maxlength: 72, required: true, autocomplete: "new-password" },
        "Mínimo 8 caracteres, con letras y números.")),
    error,
    el("button", { class: "boton boton--ancho", type: "submit" }, "Crear cuenta"));

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const datos = Object.fromEntries(new FormData(form));
    const faltan = ["documento", "nombres", "apellidos", "email", "password"].filter((k) => !datos[k]?.trim());
    if (faltan.length) {
      error.replaceChildren(el("div", { class: "aviso aviso--error" }, el("p", {}, "Completa los campos marcados.")));
      marcarInvalidos(form, faltan);
      return;
    }
    if (!datos.telefono?.trim()) delete datos.telefono;
    const boton = form.querySelector("button");
    boton.disabled = true;
    try {
      const r = await api("/auth/registro", { metodo: "POST", cuerpo: datos });
      sesionCliente.guardar(r.access_token, r.usuario, r.expira_en);
      location.reload();
    } catch (e) {
      mostrarError(error, e);
      boton.disabled = false;
    }
  });
  return form;
}

function pantallaAcceso(vista = "entrar", mensaje) {
  raiz.replaceChildren(
    el("h1", { class: "titulo-pagina" }, "Tu cuenta"),
    el("div", { class: "acceso" }, formularioEntrar(mensaje), formularioRegistro()));
  if (vista === "registro") document.getElementById("reg-documento")?.focus();
}

// ---------------------------------------------------------------------
// Mis pedidos
// ---------------------------------------------------------------------
function tarjetaPedido(p) {
  return el("li", { class: "pedido-cliente" },
    el("div", { class: "pedido-cliente__cabeza" },
      el("div", {},
        el("p", { class: "codigo-pedido" }, p.codigo_qr),
        el("p", { class: "subtitulo" }, `${fecha(p.fecha_pedido)} · ${p.sede.nombre} · ${ENTREGAS[p.tipo_entrega] || p.tipo_entrega}`)),
      el("span", { class: `estado-pedido estado-pedido--${p.estado.toLowerCase()}` }, ESTADOS[p.estado] || p.estado)),
    el("ul", { class: "lineas lineas--compactas" }, p.items.map((i) =>
      el("li", { class: "linea linea--compacta" },
        el("span", {}, `${i.cantidad} × ${i.descripcion}`), el("span", {}, precio(i.subtotal_linea))))),
    el("details", { class: "pedido-cliente__qr" },
      el("summary", {}, "Ver código para recoger"),
      qr(p.codigo_qr, { tamano: 4 })),
    el("p", { class: "pedido-cliente__total" }, el("span", {}, "Total"), el("strong", {}, precio(p.total))));
}

async function pantallaCuenta() {
  const usuario = await capi("/auth/perfil");
  const pedidos = await capi("/cuenta/pedidos?size=50");
  const cerrar = el("button", {
    class: "boton boton--secundario", type: "button",
    onclick: () => { sesionCliente.cerrar(); location.reload(); },
  }, "Cerrar sesión");

  raiz.replaceChildren(
    el("div", { class: "cuenta__cabeza" },
      el("div", {},
        el("h1", { class: "titulo-pagina" }, `Hola, ${usuario.nombres}`),
        el("p", { class: "subtitulo" }, `${usuario.email} · Documento ${usuario.documento}`)),
      cerrar),
    el("h2", {}, "Mis pedidos"),
    pedidos.items.length
      ? el("ul", { class: "pedidos-cliente" }, pedidos.items.map(tarjetaPedido))
      : el("div", { class: "aviso" }, el("p", {}, "Todavía no tienes pedidos."),
        el("p", {}, el("a", { class: "boton", href: "/" }, "Ver el catálogo"))));
}

async function iniciar() {
  try {
    await iniciarCabecera();
    if (sesionCliente.leer()) await pantallaCuenta();
    else pantallaAcceso(new URLSearchParams(location.search).get("vista") || "entrar");
  } catch (error) {
    if (error.estado !== 401) mostrarError(raiz, error, iniciar);
  }
}

iniciar();
