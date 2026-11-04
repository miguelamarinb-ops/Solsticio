// Reporte de prendas más escaneadas: ranking calculado en MongoDB (escaneos_qr)
// y completado con precio y existencias de MySQL.
import { el, fechaHora, precio, sinPrefijo } from "../comun.js";
import { campo, encabezado, papi, selector, tabla } from "./ui.js";

export async function render(principal) {
  const filtros = { dias: 30, limite: 10 };
  const zona = el("div");

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Calculando…"));
    let datos;
    try {
      datos = await papi(`/reportes/qr-mas-escaneados?dias=${filtros.dias}&limite=${filtros.limite}`);
    } catch (error) {
      if (error.estado !== 404) throw error;
      zona.replaceChildren(el("div", { class: "vacio" }, el("p", {}, `No hubo escaneos en los últimos ${filtros.dias} días.`)));
      return;
    }
    const mayor = Math.max(...datos.items.map((r) => r.escaneos.total));
    zona.replaceChildren(el("section", { class: "tarjeta" }, tabla([
      { titulo: "#", valor: (r) => String(r.posicion), clase: "num" },
      { titulo: "Prenda", valor: (r) => el("span", {}, el("strong", {}, r.descripcion), el("br"), el("small", { class: "nota" }, r.sku)) },
      { titulo: "Escaneos", valor: (r) => el("span", { class: "barra-dato" },
        el("span", { class: "barra-dato__barra", style: `--ancho:${Math.round((r.escaneos.total / mayor) * 100)}%` }),
        el("span", {}, `${r.escaneos.total} (web ${r.escaneos.web}, tienda ${r.escaneos.tienda})`)) },
      { titulo: "Último", valor: (r) => fechaHora(r.escaneos.ultimo) },
      { titulo: "Precio", valor: (r) => precio(r.precio_final), clase: "num" },
      { titulo: "Existencias", valor: (r) => el("span", { title: r.disponibilidad.map((d) => `${sinPrefijo(d.sede)}: ${d.cantidad}`).join(", "), class: r.stock_total ? "" : "texto-no" }, String(r.stock_total)), clase: "num" },
    ], datos.items),
    el("p", { class: "nota" }, "Si una prenda se escanea mucho y tiene pocas existencias, conviene reponerla o trasladarla.")));
  }

  principal.replaceChildren(
    encabezado("Prendas más escaneadas", "Qué etiquetas QR escanean más los clientes, en la tienda y desde la web."),
    el("div", { class: "filtros-barra" },
      campo("Periodo", selector("dias", [[7, "Últimos 7 días"], [30, "Últimos 30 días"], [90, "Últimos 90 días"], [365, "Último año"]], filtros.dias,
        { onchange: (e) => { filtros.dias = Number(e.target.value); cargar(); } })),
      campo("Mostrar", selector("limite", [[5, "5 prendas"], [10, "10 prendas"], [20, "20 prendas"]], filtros.limite,
        { onchange: (e) => { filtros.limite = Number(e.target.value); cargar(); } }))),
    zona);
  await cargar();
}
