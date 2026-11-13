// Reportes del administrador (caso de uso 2.3.9).
// Ventas, prendas más vendidas y rotación salen de MySQL; las prendas más escaneadas
// salen de MongoDB (escaneos_qr) completadas con precio y existencias de MySQL.
import { el, fecha, fechaHora, precio, sinPrefijo } from "../comun.js";
import { campo, encabezado, insignia, opcionesSedes, papi, pestanas, selector, tabla } from "./ui.js";

const VISTAS = [
  ["ventas", "Ventas"],
  ["mas-vendidas", "Más vendidas"],
  ["rotacion", "Rotación de inventario"],
  ["qr", "Más escaneadas"],
];
const TONO_ROTACION = { ALTA: "verde", MEDIA: "azul", BAJA: "sol", SIN_VENTAS: "gris" };
const NUMERICOS = new Set(["limite", "dias"]);

// Fecha local (no UTC): de noche en Colombia, toISOString ya marca el día siguiente.
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const haceDias = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return iso(d); };
const numero = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

function cifra(valor, texto, tono) {
  return el("div", { class: `cifra${tono ? ` cifra--${tono}` : ""}` }, el("strong", {}, valor), el("span", {}, texto));
}

function barra(valor, mayor, texto) {
  const ancho = mayor ? Math.round((valor / mayor) * 100) : 0;
  return el("span", { class: "barra-dato" },
    el("span", { class: "barra-dato__barra", style: `--ancho:${ancho}%` }), el("span", {}, texto));
}

export async function render(principal, ctx, { vista = "ventas" }) {
  if (!VISTAS.some(([v]) => v === vista)) vista = "ventas";
  const q = ctx.consulta();
  const filtros = {
    desde: q.get("desde") || haceDias(29),
    hasta: q.get("hasta") || iso(new Date()),
    id_sede: q.get("id_sede") || "",
    canal: q.get("canal") || "",
    limite: Number(q.get("limite")) || 10,
    dias: Number(q.get("dias")) || 30,
  };
  const zona = el("div");
  const pintores = { ventas, "mas-vendidas": masVendidas, rotacion, qr };

  async function cargar() {
    zona.replaceChildren(el("p", { class: "cargando" }, "Calculando…"));
    await pintores[vista](zona, filtros);
  }

  const control = (nombre, nodo) => {
    nodo.addEventListener("change", (e) => {
      filtros[nombre] = NUMERICOS.has(nombre) ? Number(e.target.value) : e.target.value;
      cargar();
    });
    return nodo;
  };
  const fechas = [
    campo("Desde", control("desde", el("input", { type: "date", value: filtros.desde, max: iso(new Date()) }))),
    campo("Hasta", control("hasta", el("input", { type: "date", value: filtros.hasta, max: iso(new Date()) }))),
  ];
  const sede = campo("Sede", control("id_sede", selector("id_sede", opcionesSedes(ctx.sedes, "Todas las sedes"), filtros.id_sede)));
  const barras = {
    ventas: [...fechas, sede,
      campo("Canal", control("canal", selector("canal", [["", "Web y tienda"], ["WEB", "Web"], ["TIENDA", "Tienda"]], filtros.canal)))],
    "mas-vendidas": [...fechas, sede,
      campo("Mostrar", control("limite", selector("limite", [[5, "5 prendas"], [10, "10 prendas"], [20, "20 prendas"]], filtros.limite)))],
    rotacion: [...fechas, sede],
    qr: [
      campo("Periodo", control("dias", selector("dias", [[7, "Últimos 7 días"], [30, "Últimos 30 días"], [90, "Últimos 90 días"], [365, "Último año"]], filtros.dias))),
      campo("Mostrar", control("limite", selector("limite", [[5, "5 prendas"], [10, "10 prendas"], [20, "20 prendas"]], filtros.limite)))],
  };

  principal.replaceChildren(
    encabezado("Reportes", "Ventas, prendas más vendidas, rotación del inventario y escaneos de etiquetas QR."),
    pestanas(VISTAS.map(([v, texto]) => [v === "ventas" ? "#/reportes" : `#/reportes/${v}`, texto]),
      vista === "ventas" ? "#/reportes" : `#/reportes/${vista}`),
    el("div", { class: "filtros-barra" }, barras[vista]),
    zona);
  await cargar();
}

function parametros(filtros, nombres) {
  const p = new URLSearchParams();
  for (const n of nombres) if (filtros[n] !== "" && filtros[n] != null) p.set(n, filtros[n]);
  return p;
}

// ---------------------------------------------------------------------
async function ventas(zona, filtros) {
  const r = await papi(`/reportes/ventas?${parametros(filtros, ["desde", "hasta", "id_sede", "canal"])}`);
  const s = r.resumen;
  const mayorDia = Math.max(0, ...r.por_dia.map((d) => Number(d.ingresos)));
  const mayorCanal = Math.max(0, ...r.por_canal.map((c) => Number(c.ingresos)));
  zona.replaceChildren(
    el("section", { class: "cifras", "aria-label": "Resumen de ventas" },
      cifra(precio(s.ingresos_netos), "ingresos netos", "azul"),
      cifra(String(s.total_pedidos), `pedidos pagados, ${s.unidades_vendidas} prendas`),
      cifra(precio(s.ticket_promedio), "ticket promedio"),
      cifra(String(s.devoluciones), `devoluciones, ${precio(s.monto_devuelto)}`, s.devoluciones ? "sol" : null)),
    el("div", { class: "rejilla-panel" },
      el("section", { class: "tarjeta" },
        el("h2", {}, "Por canal"),
        tabla([
          { titulo: "Canal", valor: (c) => insignia(c.canal) },
          { titulo: "Pedidos", valor: (c) => String(c.pedidos), clase: "num" },
          { titulo: "Ingresos", valor: (c) => barra(Number(c.ingresos), mayorCanal, precio(c.ingresos)) },
        ], r.por_canal),
        el("p", { class: "nota" }, `Ingresos brutos ${precio(s.ingresos_brutos)} menos ${precio(s.monto_devuelto)} en notas crédito.`)),
      el("section", { class: "tarjeta" },
        el("h2", {}, "Por día"),
        tabla([
          { titulo: "Día", valor: (d) => fecha(`${d.fecha}T12:00:00`) },
          { titulo: "Pedidos", valor: (d) => String(d.pedidos), clase: "num" },
          { titulo: "Ingresos", valor: (d) => barra(Number(d.ingresos), mayorDia, precio(d.ingresos)) },
        ], r.por_dia, { vacio: "No hubo ventas pagadas en este periodo." }))),
    el("p", { class: "nota" }, "Cuentan los pedidos pagados (pagado, preparando, enviado o entregado). Los montos son los de cada venta, no el precio actual del catálogo."));
}

// ---------------------------------------------------------------------
async function masVendidas(zona, filtros) {
  const r = await papi(`/reportes/productos-mas-vendidos?${parametros(filtros, ["desde", "hasta", "id_sede", "limite"])}`);
  const mayor = Math.max(0, ...r.items.map((i) => i.unidades_vendidas));
  zona.replaceChildren(el("section", { class: "tarjeta" }, tabla([
    { titulo: "#", valor: (i) => String(i.posicion), clase: "num" },
    { titulo: "Prenda", valor: (i) => el("span", {}, el("strong", {}, i.producto), el("br"), el("small", { class: "nota" }, i.categoria)) },
    { titulo: "Unidades", valor: (i) => barra(i.unidades_vendidas, mayor, `${i.unidades_vendidas} ${i.unidades_vendidas === 1 ? "vendida" : "vendidas"}`) },
    { titulo: "Talla más vendida", valor: (i) => i.talla_mas_vendida || "—" },
    { titulo: "Ingresos", valor: (i) => precio(i.ingresos), clase: "num" },
  ], r.items, { vacio: "No hubo ventas pagadas en este periodo." })));
}

// ---------------------------------------------------------------------
async function rotacion(zona, filtros) {
  const r = await papi(`/reportes/rotacion-inventario?${parametros(filtros, ["desde", "hasta", "id_sede"])}`);
  const res = r.resumen;
  zona.replaceChildren(
    el("section", { class: "cifras", "aria-label": "Prendas por rotación" },
      cifra(String(res.ALTA), "rotación alta (1 o más)", "azul"),
      cifra(String(res.MEDIA), "rotación media"),
      cifra(String(res.BAJA), "rotación baja (menos de 0,3)", res.BAJA ? "sol" : null),
      cifra(String(res.SIN_VENTAS), "sin ventas en el periodo", res.SIN_VENTAS ? "rojo" : null)),
    el("section", { class: "tarjeta" }, tabla([
      { titulo: "Prenda", valor: (i) => el("span", {}, el("strong", {}, i.producto), el("br"), el("small", { class: "nota" }, i.categoria)) },
      { titulo: "Vendidas", valor: (i) => String(i.unidades_vendidas), clase: "num" },
      { titulo: "Stock inicial", valor: (i) => String(i.stock_inicial), clase: "num" },
      { titulo: "Stock final", valor: (i) => String(i.stock_final), clase: "num" },
      { titulo: "Rotación", valor: (i) => (i.indice_rotacion == null ? "—" : numero.format(i.indice_rotacion)), clase: "num" },
      { titulo: "Días de inventario", valor: (i) => (i.dias_inventario == null ? "—" : String(i.dias_inventario)), clase: "num" },
      { titulo: "", valor: (i) => insignia(i.clasificacion, TONO_ROTACION[i.clasificacion]) },
    ], r.items, { vacio: "No hay existencias ni movimientos en esta sede." }),
    el("p", { class: "nota" }, "Rotación = unidades vendidas ÷ existencias promedio del periodo. Días de inventario = cuánto alcanza el stock final al ritmo de venta del periodo. Las prendas sin ventas y con mucho stock son candidatas a traslado o promoción.")));
}

// ---------------------------------------------------------------------
async function qr(zona, filtros) {
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
    { titulo: "Escaneos", valor: (r) => barra(r.escaneos.total, mayor, `${r.escaneos.total} (web ${r.escaneos.web}, tienda ${r.escaneos.tienda})`) },
    { titulo: "Último", valor: (r) => fechaHora(r.escaneos.ultimo) },
    { titulo: "Precio", valor: (r) => precio(r.precio_final), clase: "num" },
    { titulo: "Existencias", valor: (r) => el("span", { title: r.disponibilidad.map((d) => `${sinPrefijo(d.sede)}: ${d.cantidad}`).join(", "), class: r.stock_total ? "" : "texto-no" }, String(r.stock_total)), clase: "num" },
  ], datos.items),
  el("p", { class: "nota" }, "Escaneos guardados en MongoDB. Si una prenda se escanea mucho y tiene pocas existencias, conviene reponerla o trasladarla.")));
}
