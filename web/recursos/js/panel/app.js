// Panel del personal: inicio de sesión, menú según el rol y enrutador por hash
// (#/pedidos/12). Cada sección es un módulo que exporta render(principal, ctx, params).
import { api, el, marcarInvalidos, sinPrefijo } from "../comun.js";
import { aviso, configurarExpiracion, papi, sesion } from "./ui.js";

const raiz = document.getElementById("app");

// ruta: [módulo, solo administrador, título del menú]
const RUTAS = [
  ["", "inicio", false],
  ["mostrador", "mostrador", false],
  ["pedidos", "pedidos", false],
  ["pedidos/:id", "pedido", false],
  ["inventario", "inventario", false],
  ["inventario/:vista", "inventario", false],
  ["devoluciones", "devoluciones", false],
  ["devoluciones/nueva", "devolucion-nueva", false],
  ["devoluciones/:id", "devolucion", false],
  ["traslados", "traslados", false],
  ["traslados/nuevo", "traslado-nuevo", true],
  ["traslados/:id", "traslado", false],
  ["productos", "productos", true],
  ["productos/nuevo", "producto", true],
  ["productos/:id", "producto", true],
  ["productos/:id/:vista", "producto", true],
  ["maestros", "maestros", true],
  ["opiniones", "opiniones", true],
  ["usuarios", "usuarios", true],
  ["bitacora", "bitacora", true],
  ["reportes", "reportes", true],
  ["reportes/:vista", "reportes", true],
  ["perfil", "perfil", false],
];

const MENU = [
  ["Operación", [["#/", "Inicio"], ["#/mostrador", "Mostrador"], ["#/pedidos", "Pedidos"], ["#/devoluciones", "Devoluciones"], ["#/inventario", "Inventario"], ["#/traslados", "Traslados"]]],
  ["Catálogo", [["#/productos", "Prendas", true], ["#/maestros", "Categorías y sedes", true], ["#/opiniones", "Opiniones", true]]],
  ["Administración", [["#/usuarios", "Usuarios", true], ["#/bitacora", "Bitácora", true], ["#/reportes", "Reportes", true]]],
];

let ctx = null;

function resolver(hash) {
  const partes = hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean);
  for (const [patron, modulo, soloAdmin] of RUTAS) {
    const piezas = patron.split("/").filter(Boolean);
    if (piezas.length !== partes.length) continue;
    const params = {};
    const coincide = piezas.every((p, i) => {
      if (p.startsWith(":")) { params[p.slice(1)] = decodeURIComponent(partes[i]); return true; }
      return p === partes[i];
    });
    if (coincide) return { modulo, soloAdmin, params };
  }
  return null;
}

export const consulta = () => new URLSearchParams(location.hash.split("?")[1] || "");
export const navegar = (ruta) => { location.hash = ruta; };

// ---------------------------------------------------------------------
// Inicio de sesión
// ---------------------------------------------------------------------
function pantallaLogin(mensaje) {
  const error = el("p", { class: "texto-no", role: "alert" }, mensaje || "");
  const form = el("form", { class: "login__form", novalidate: true },
    el("h1", {}, "Panel del personal"),
    el("p", { class: "nota" }, "Entra con el correo y la contraseña que te dio el administrador."),
    el("div", { class: "campo" }, el("label", { for: "login-email" }, "Correo"),
      el("input", { id: "login-email", name: "email", type: "email", autocomplete: "username", required: true })),
    el("div", { class: "campo" }, el("label", { for: "login-clave" }, "Contraseña"),
      el("input", { id: "login-clave", name: "password", type: "password", autocomplete: "current-password", required: true })),
    error,
    el("button", { class: "boton boton--ancho", type: "submit" }, "Entrar"),
    el("p", { class: "nota" }, el("a", { href: "/" }, "Volver a la tienda")));

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const datos = Object.fromEntries(new FormData(form));
    if (!datos.email || !datos.password) {
      error.textContent = "Escribe tu correo y tu contraseña.";
      marcarInvalidos(form, ["email", "password"].filter((k) => !datos[k]));
      return;
    }
    const boton = form.querySelector("button");
    boton.disabled = true;
    try {
      const r = await api("/auth/login", { metodo: "POST", cuerpo: datos });
      if (r.usuario.rol === "CLIENTE") {
        error.replaceChildren("El panel es solo para el personal. ",
          el("a", { href: "/cuenta" }, "Entra a tu cuenta de cliente"), ".");
        boton.disabled = false;
        return;
      }
      sesion.guardar(r.access_token, r.usuario, r.expira_en);
      await arrancar();
    } catch (e) {
      error.textContent = e.estado === 401 ? "El correo o la contraseña no coinciden." : e.message;
      boton.disabled = false;
    }
  });

  raiz.replaceChildren(el("main", { class: "login", id: "principal" },
    el("div", { class: "login__marca" },
      el("p", { class: "marca" }, "SOLSTICIO"),
      el("p", {}, "Ventas en tienda, pedidos, inventario y catálogo de las sedes de Bogotá.")),
    form));
  form.querySelector("input").focus();
}

configurarExpiracion((mensaje) => { ctx = null; pantallaLogin(mensaje); });

// ---------------------------------------------------------------------
// Estructura y enrutado
// ---------------------------------------------------------------------
function estructura() {
  const { usuario, esAdmin } = ctx;
  const enlaces = MENU.map(([grupo, items]) => {
    const visibles = items.filter(([, , soloAdmin]) => esAdmin || !soloAdmin);
    if (!visibles.length) return null;
    return el("div", { class: "menu__grupo" }, el("p", {}, grupo),
      el("ul", {}, visibles.map(([href, texto]) => el("li", {}, el("a", { href, "data-menu": href }, texto)))));
  });

  const menu = el("nav", { class: "menu", id: "menu", "aria-label": "Panel" },
    el("a", { class: "marca", href: "#/" }, "SOLSTICIO"),
    el("p", { class: "menu__subtitulo" }, "Panel del personal"),
    enlaces,
    el("div", { class: "menu__usuario" },
      el("a", { href: "#/perfil", "data-menu": "#/perfil" }, `${usuario.nombres} ${usuario.apellidos}`),
      el("p", {}, esAdmin ? "Administración, todas las sedes" : `Trabajador, ${sinPrefijo(usuario.sede?.nombre)}`),
      el("div", { class: "menu__enlaces" },
        el("a", { href: "/", target: "_blank", rel: "noopener" }, "Ver tienda"),
        el("button", { type: "button", onclick: cerrarSesion }, "Cerrar sesión"))));

  const botonMenu = el("button", { class: "menu__abrir", type: "button", "aria-controls": "menu", "aria-expanded": "false" }, "Menú");
  // Menú del celular: el foco entra al abrir, Escape lo cierra y el foco vuelve al botón.
  const cerrarMenu = (devolverFoco) => {
    if (!menu.classList.contains("menu--abierto")) return;
    menu.classList.remove("menu--abierto");
    botonMenu.setAttribute("aria-expanded", "false");
    if (devolverFoco) botonMenu.focus();
  };
  botonMenu.addEventListener("click", () => {
    const abierto = menu.classList.toggle("menu--abierto");
    botonMenu.setAttribute("aria-expanded", String(abierto));
    if (abierto) menu.querySelector(".menu__grupo a")?.focus();
  });
  menu.addEventListener("click", (e) => { if (e.target.closest("a")) cerrarMenu(false); });
  menu.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarMenu(true); });

  raiz.replaceChildren(el("div", { class: "panel" },
    el("div", { class: "panel__barra" }, el("a", { class: "marca", href: "#/" }, "SOLSTICIO"), botonMenu),
    menu,
    el("main", { class: "panel__principal", id: "principal" })));
}

function marcarMenu() {
  const hash = location.hash.split("?")[0] || "#/";
  const base = `#/${hash.replace(/^#\/?/, "").split("/")[0]}`;
  for (const a of document.querySelectorAll("[data-menu]")) {
    a.toggleAttribute("aria-current", a.dataset.menu === base || (base === "#/" && a.dataset.menu === "#/"));
    if (a.hasAttribute("aria-current")) a.setAttribute("aria-current", "page");
  }
}

async function enrutar() {
  if (!ctx) return;
  const principal = document.getElementById("principal");
  const destino = resolver(location.hash);
  marcarMenu();
  if (!destino || (destino.soloAdmin && !ctx.esAdmin)) {
    principal.replaceChildren(el("div", { class: "aviso" },
      el("p", {}, destino ? "Esta sección es solo para administración." : "Esa página no existe."),
      el("p", {}, el("a", { href: "#/" }, "Ir al inicio"))));
    return;
  }
  principal.replaceChildren(el("p", { class: "cargando" }, "Cargando…"));
  try {
    const modulo = await import(`./${destino.modulo}.js`);
    await modulo.render(principal, ctx, destino.params);
    principal.querySelector("h1")?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  } catch (error) {
    if (error.estado === 401) return;
    principal.replaceChildren(el("div", { class: "aviso aviso--error", role: "alert" },
      el("p", {}, error.estado === 404 ? "No encontramos lo que buscas." : error.message),
      el("p", {}, el("button", { class: "boton boton--secundario", type: "button", onclick: enrutar }, "Intentar de nuevo"))));
  }
}

function cerrarSesion() {
  sesion.cerrar();
  ctx = null;
  aviso("Cerraste sesión.");
  history.replaceState(null, "", "/panel");
  pantallaLogin();
}

async function arrancar() {
  const guardada = sesion.leer();
  if (!guardada) { pantallaLogin(); return; }
  try {
    const usuario = await papi("/auth/perfil");
    const sedes = await api("/sedes");
    ctx = { usuario, sedes, esAdmin: usuario.rol === "ADMINISTRADOR", navegar, consulta, refrescar: enrutar };
  } catch {
    return;   // papi ya mostró el login si el token venció
  }
  estructura();
  await enrutar();
}

window.addEventListener("hashchange", enrutar);
arrancar();
