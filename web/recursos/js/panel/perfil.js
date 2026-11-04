// Mi perfil: datos del usuario (MySQL) junto a sus últimas acciones (MongoDB).
// Es el endpoint combinado GET /auth/perfil/actividad.
import { el, fecha, fechaHora, sinPrefijo } from "../comun.js";
import { datos, encabezado, legible, papi, tabla } from "./ui.js";

export async function render(principal) {
  const r = await papi("/auth/perfil/actividad?limite=15");
  const u = r.usuario;
  const mayor = Math.max(1, ...r.resumen_actividad.map((a) => a.veces));
  principal.replaceChildren(
    encabezado("Mi perfil", "Tus datos y lo último que hiciste en el sistema."),
    el("div", { class: "rejilla-panel rejilla-panel--detalle" },
      el("section", { class: "tarjeta" },
        el("h2", {}, `${u.nombres} ${u.apellidos}`),
        datos([["Correo", u.email], ["Documento", u.documento], ["Rol", u.rol === "ADMINISTRADOR" ? "Administración" : "Trabajador"],
          ["Sede", u.sede ? sinPrefijo(u.sede.nombre) : "Todas"], ["En el sistema desde", fecha(r.fecha_registro)]]),
        el("p", { class: "nota" }, "Datos de MySQL.")),
      el("section", { class: "tarjeta" },
        el("h2", {}, "Lo que más haces"),
        el("ul", { class: "barras" }, r.resumen_actividad.slice(0, 8).map((a) => el("li", {},
          el("span", {}, legible(a.accion.includes(".") ? a.accion.split(".")[1] : a.accion)),
          el("span", { class: "barra-dato__barra", style: `--ancho:${Math.round((a.veces / mayor) * 100)}%` }),
          el("strong", {}, String(a.veces))))),
        el("p", { class: "nota" }, "Calculado en MongoDB con una agregación."))),
    el("section", { class: "tarjeta" },
      el("h2", {}, "Tus últimas acciones"),
      tabla([
        { titulo: "Cuándo", valor: (a) => fechaHora(a.fecha) },
        { titulo: "Acción", valor: (a) => legible(a.accion.includes(".") ? a.accion.split(".")[1] : a.accion) },
        { titulo: "Petición", valor: (a) => el("small", {}, `${a.metodo} ${a.ruta}`) },
        { titulo: "Resultado", valor: (a) => el("span", { class: a.exito ? "texto-si" : "texto-no" }, String(a.estado_http)) },
      ], r.ultimas_actividades, { vacio: "Todavía no hay actividad." })));
}
