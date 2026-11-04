// Escáner de la etiqueta QR de una prenda. Con cámara usa BarcodeDetector cuando
// el navegador lo trae (Chrome en Android, por ejemplo); siempre se puede escribir
// el código a mano. Cada consulta queda registrada en MongoDB (escaneos_qr).
import { api, carrito, el, foto, iniciarCabecera, precio, sinPrefijo } from "./comun.js";

const resultado = document.getElementById("resultado");
const form = document.getElementById("form-codigo");
const campo = document.getElementById("codigo");
const video = document.getElementById("video");
const botonCamara = document.getElementById("activar-camara");
const estadoCamara = document.getElementById("estado-camara");

let cabecera;
let flujo = null;

async function consultar(codigo) {
  codigo = codigo.trim().toUpperCase();
  if (!codigo) return;
  resultado.replaceChildren(el("p", { class: "cargando" }, `Buscando ${codigo}…`));
  try {
    const sede = cabecera.sedeActual();
    const datos = await api(`/variantes/qr/${encodeURIComponent(codigo)}${sede ? `?sede=${sede}` : ""}`);
    pintar(datos);
  } catch (error) {
    resultado.replaceChildren(el("div", { class: "aviso aviso--error", role: "alert" },
      el("p", {}, error.estado === 404
        ? `El código ${codigo} no corresponde a ninguna prenda. Revisa que esté bien escrito.`
        : error.message)));
  }
}

function pintar(v) {
  const mia = v.disponibilidad.find((d) => d.id_sede === cabecera.sedeActual());
  const hayAqui = (mia?.cantidad ?? 0) > 0;
  const boton = el("button", { class: "boton boton--compra", type: "button", disabled: !hayAqui }, "Agregar al carrito");
  boton.addEventListener("click", () => {
    carrito.agregar({
      id_variante: v.id_variante, id_producto: v.producto.id_producto, nombre: v.producto.nombre,
      talla: v.talla, color: v.color, precio: v.precio_final, imagen: v.producto.imagen_principal,
    });
    boton.replaceWith(el("p", { class: "texto-si" }, "Agregada al carrito. ", el("a", { href: "/carrito" }, "Ver carrito")));
  });

  resultado.replaceChildren(el("article", { class: "ficha-qr" },
    el("div", { class: "ficha-qr__foto" }, foto(v.producto.imagen_principal, v.producto.nombre, { lazy: false })),
    el("div", {},
      el("p", { class: "detalle__categoria" }, `Código ${v.codigo_qr}`),
      el("h2", { class: "ficha-qr__nombre" }, v.producto.nombre),
      el("p", {}, `Talla ${v.talla}, ${v.color}`),
      el("div", { class: "colgante" }, el("span", {}, precio(v.precio_final))),
      el("ul", { class: "sedes" }, v.disponibilidad.map((d) =>
        el("li", { class: d.id_sede === cabecera.sedeActual() ? "es-mia" : null },
          el("span", {}, sinPrefijo(d.sede), d.id_sede === cabecera.sedeActual() ? " (tu sede)" : ""),
          el("span", { class: d.cantidad ? "" : "texto-no" }, d.cantidad ? String(d.cantidad) : "Agotado")))),
      el("div", { class: "compra__fila" }, boton,
        el("a", { class: "boton boton--secundario", href: `/producto?id=${v.producto.id_producto}` }, "Ver la prenda")),
    )));
}

form.addEventListener("submit", (evento) => {
  evento.preventDefault();
  consultar(campo.value);
});

// ---------------------------------------------------------------------
// Cámara
// ---------------------------------------------------------------------
async function activarCamara() {
  if (!("BarcodeDetector" in window)) {
    estadoCamara.textContent = "Este navegador no puede leer códigos con la cámara. Escribe el código a mano.";
    return;
  }
  try {
    flujo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
  } catch {
    estadoCamara.textContent = "No pudimos usar la cámara. Revisa el permiso del navegador o escribe el código.";
    return;
  }
  const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
  video.srcObject = flujo;
  video.hidden = false;
  botonCamara.hidden = true;
  estadoCamara.textContent = "Apunta al QR de la etiqueta.";
  await video.play();

  const leer = async () => {
    if (!flujo) return;
    try {
      const [codigo] = await detector.detect(video);
      if (codigo?.rawValue) {
        detenerCamara();
        campo.value = codigo.rawValue;
        consultar(codigo.rawValue);
        return;
      }
    } catch { /* cuadro sin código: se intenta de nuevo */ }
    requestAnimationFrame(leer);
  };
  leer();
}

function detenerCamara() {
  flujo?.getTracks().forEach((pista) => pista.stop());
  flujo = null;
  video.hidden = true;
  botonCamara.hidden = false;
  botonCamara.textContent = "Escanear otro";
  estadoCamara.textContent = "";
}

botonCamara.addEventListener("click", activarCamara);

async function iniciar() {
  cabecera = await iniciarCabecera({ alCambiarSede: () => campo.value && consultar(campo.value) });
  const desdeUrl = new URLSearchParams(location.search).get("codigo");
  if (desdeUrl) {
    campo.value = desdeUrl;
    consultar(desdeUrl);
  }
  if (!("BarcodeDetector" in window)) {
    botonCamara.hidden = true;
    estadoCamara.textContent = "Desde el celular, apunta la cámara al QR y se abre esta página sola. Aquí puedes escribir el código.";
  }
}

iniciar();
