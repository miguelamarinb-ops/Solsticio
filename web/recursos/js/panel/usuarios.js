// Usuarios del personal (administración): crear, activar o desactivar el acceso.
import { el, sinPrefijo } from "../comun.js";
import { aviso, campo, confirmar, encabezado, errorEn, insignia, opcionesSedes, papi, selector, tabla } from "./ui.js";

export async function render(principal, ctx) {
  const usuarios = await papi("/usuarios");
  const zonaError = el("div");

  async function cambiar(u) {
    const activar = !u.activo;
    if (!activar && !await confirmar("Desactivar usuario", `${u.nombres} ${u.apellidos} ya no podrá iniciar sesión.`, { accion: "Desactivar", peligro: true })) return;
    try {
      await papi(`/usuarios/${u.id_usuario}`, { metodo: "PATCH", cuerpo: { activo: activar } });
      aviso(activar ? "Usuario activado." : "Usuario desactivado.");
      render(principal, ctx);
    } catch (error) { errorEn(zonaError, error); }
  }

  const sedeCampo = campo("Sede", selector("id_sede", opcionesSedes(ctx.sedes), ctx.sedes[0]?.id_sede));
  const rol = selector("rol", [["TRABAJADOR", "Trabajador de sede"], ["ADMINISTRADOR", "Administración"]], "TRABAJADOR");
  rol.addEventListener("change", () => { sedeCampo.hidden = rol.value !== "TRABAJADOR"; });
  const errorForm = el("div");
  const form = el("form", { class: "tarjeta", novalidate: true },
    el("h2", {}, "Nuevo usuario"),
    el("div", { class: "campos" },
      campo("Nombres", el("input", { name: "nombres", maxlength: 80, required: true })),
      campo("Apellidos", el("input", { name: "apellidos", maxlength: 80, required: true })),
      campo("Documento", el("input", { name: "documento", maxlength: 20, required: true, inputmode: "numeric" })),
      campo("Correo", el("input", { name: "email", type: "email", maxlength: 120, required: true, autocomplete: "off" })),
      campo("Contraseña inicial", el("input", { name: "password", type: "password", minlength: 8, required: true, autocomplete: "new-password" }), "Mínimo 8 caracteres."),
      campo("Rol", rol),
      sedeCampo),
    errorForm,
    el("button", { class: "boton", type: "submit" }, "Crear usuario"));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorForm.replaceChildren();
    const f = Object.fromEntries(new FormData(form));
    const cuerpo = { nombres: f.nombres.trim(), apellidos: f.apellidos.trim(), documento: f.documento.trim(), email: f.email.trim(), password: f.password, rol: f.rol };
    if (f.rol === "TRABAJADOR") cuerpo.id_sede = Number(f.id_sede);
    if (Object.values(cuerpo).some((v) => v === "")) { errorEn(errorForm, new Error("Completa todos los campos.")); return; }
    try {
      await papi("/usuarios", { metodo: "POST", cuerpo });
      aviso("Usuario creado. Entrégale su correo y contraseña inicial.");
      render(principal, ctx);
    } catch (error) { errorEn(errorForm, error); }
  });

  principal.replaceChildren(
    encabezado("Usuarios", "Quién puede entrar al panel y en qué sede trabaja."),
    zonaError,
    el("div", { class: "rejilla-panel rejilla-panel--detalle" },
      el("section", { class: "tarjeta" },
        tabla([
          { titulo: "Nombre", valor: (u) => el("strong", {}, `${u.nombres} ${u.apellidos}`) },
          { titulo: "Correo", valor: (u) => u.email },
          { titulo: "Rol", valor: (u) => (u.rol === "ADMINISTRADOR" ? "Administración" : "Trabajador") },
          { titulo: "Sede", valor: (u) => (u.sede ? sinPrefijo(u.sede.nombre) : "Todas") },
          { titulo: "Estado", valor: (u) => insignia(u.activo ? "ACTIVO" : "INACTIVO") },
          { titulo: "", valor: (u) => el("span", { class: "acciones-fila" },
            el("a", { href: `#/bitacora?id_usuario=${u.id_usuario}` }, "Actividad"),
            u.id_usuario === ctx.usuario.id_usuario ? null
              : el("button", { class: "enlace-boton", type: "button", onclick: () => cambiar(u) }, u.activo ? "Desactivar" : "Activar")) },
        ], usuarios)),
      form));
}
