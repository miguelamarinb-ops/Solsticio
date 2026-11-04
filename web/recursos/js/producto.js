// Detalle de una prenda. Usa /productos/{id}/completo, que junta MySQL (precio,
// variantes, stock por sede) y MongoDB (ficha técnica, opiniones, escaneos).
import { api, carrito, el, estrellas, fecha, foto, iniciarCabecera, mostrarError, precio } from "./comun.js";
import { etiqueta, nombreAtributo } from "./etiqueta.js";

const contenedor = document.getElementById("producto");
const id = Number(new URLSearchParams(location.search).get("id"));

let producto;
let cabecera;
let seleccion = { talla: null, color: null };

// ---------------------------------------------------------------------
// Variantes y disponibilidad (MySQL)
// ---------------------------------------------------------------------
const tallas = () => [...new Set(producto.variantes.map((v) => v.talla))];
const coloresDe = (talla) => producto.variantes.filter((v) => v.talla === talla);
const varianteElegida = () =>
  producto.variantes.find((v) => v.talla === seleccion.talla && v.color.nombre === seleccion.color);

function cantidadEnMiSede(variante) {
  return variante.disponibilidad.find((d) => d.id_sede === cabecera.sedeActual())?.cantidad ?? 0;
}

function elegirInicial() {
  const variantes = producto.variantes;
  const elegida = variantes.find((v) => cantidadEnMiSede(v) > 0) || variantes.find((v) => v.stock_total > 0) || variantes[0];
  seleccion = { talla: elegida.talla, color: elegida.color.nombre };
}

function grupoOpciones(nombre, leyenda, opciones) {
  return el("fieldset", { class: "opciones" },
    el("legend", {}, leyenda),
    el("div", { class: "opciones__lista" }, opciones.map(({ valor, contenido, marcada }) =>
      el("label", { class: "opcion" },
        el("input", { type: "radio", name: nombre, value: valor, checked: marcada }),
        el("span", {}, contenido)))));
}

function pintarCompra() {
  const zona = document.getElementById("zona-compra");
  const variante = varianteElegida();
  const sedeMia = cabecera.sedeActual();
  const mayor = Math.max(10, ...variante.disponibilidad.map((d) => d.cantidad));
  const enMiSede = cantidadEnMiSede(variante);
  const otras = variante.disponibilidad.filter((d) => d.cantidad > 0 && d.id_sede !== sedeMia).map((d) => d.sede.replace(/^Solsticio\s+/, ""));
  const corto = (nombre) => nombre.replace(/^Solsticio\s+/, "");
  const nombreMiSede = corto(variante.disponibilidad.find((d) => d.id_sede === sedeMia)?.sede ?? "tu sede");

  let resumen;
  if (enMiSede > 0) {
    resumen = el("p", { class: "texto-si" }, `Hay ${enMiSede} ${enMiSede === 1 ? "unidad" : "unidades"} en ${nombreMiSede}.`);
  } else if (otras.length) {
    resumen = el("p", {}, el("span", { class: "texto-no" }, `Agotado en ${nombreMiSede}. `), `Lo encuentras en ${otras.join(" y ")}.`);
  } else {
    resumen = el("p", { class: "texto-no" }, "Agotado en todas las sedes por ahora.");
  }

  zona.replaceChildren(
    el("div", { class: "colgante" }, el("span", {}, precio(variante.precio_final))),
    grupoOpciones("talla", "Talla", tallas().map((t) => ({ valor: t, contenido: t, marcada: t === seleccion.talla }))),
    grupoOpciones("color", "Color", coloresDe(seleccion.talla).map((v) => ({
      valor: v.color.nombre,
      marcada: v.color.nombre === seleccion.color,
      contenido: [el("span", { class: "muestra-color", style: `background:${v.color.codigo_hex || "#ccc"}`, "aria-hidden": "true" }), v.color.nombre],
    }))),
    el("div", { "aria-live": "polite" }, resumen),
    bloqueCompra(variante, enMiSede, nombreMiSede),
    el("p", { class: "sedes__titulo" }, "Disponibilidad por sede"),
    el("ul", { class: "sedes" }, variante.disponibilidad.map((d) =>
      el("li", { class: d.id_sede === sedeMia ? "es-mia" : null },
        el("span", {}, d.sede.replace(/^Solsticio\s+/, ""), d.id_sede === sedeMia ? " (tu sede)" : ""),
        el("span", { class: d.cantidad ? "" : "texto-no" }, d.cantidad ? `${d.cantidad}` : "Agotado"),
        el("span", { class: "sedes__barra", "aria-hidden": "true" },
          el("span", { style: `width:${Math.round((d.cantidad / mayor) * 100)}%` }))))),
  );
}

// El pedido web se arma en la sede elegida: solo se puede llevar lo que hay allí.
function bloqueCompra(variante, enMiSede, nombreMiSede) {
  const enCarrito = carrito.items().find((i) => i.id_variante === variante.id_variante)?.cantidad ?? 0;
  const maximo = Math.max(enMiSede - enCarrito, 0);
  if (!enMiSede) {
    return el("p", { class: "nota-compra" }, `Para comprarla, elige arriba una sede donde haya existencias.`);
  }
  const cantidad = el("input", {
    id: "cantidad", type: "number", min: 1, max: Math.max(maximo, 1), value: 1, inputmode: "numeric",
    disabled: !maximo,
  });
  const aviso = el("p", { class: "nota-compra", role: "status" },
    enCarrito ? `Ya tienes ${enCarrito} en el carrito.` : "");
  const boton = el("button", { class: "boton boton--compra", type: "button", disabled: !maximo }, "Agregar al carrito");
  boton.addEventListener("click", () => {
    const n = Math.min(Math.max(Number(cantidad.value) || 1, 1), maximo);
    carrito.agregar({
      id_variante: variante.id_variante, id_producto: producto.id_producto, nombre: producto.nombre,
      talla: variante.talla, color: variante.color.nombre, precio: variante.precio_final,
      imagen: (producto.imagenes.find((i) => i.es_principal) || producto.imagenes[0])?.url || null,
    }, n);
    pintarCompra();
    const nota = document.querySelector(".nota-compra");
    nota.replaceChildren(`Agregaste ${n} al carrito para recoger o enviar desde ${nombreMiSede}. `,
      el("a", { href: "/carrito" }, "Ver carrito"));
  });
  return el("div", { class: "compra" },
    el("div", { class: "compra__fila" },
      el("label", { class: "compra__cantidad" }, el("span", {}, "Cantidad"), cantidad),
      boton),
    aviso,
    !maximo ? el("p", { class: "nota-compra" }, `Ya tienes en el carrito todo lo que hay en ${nombreMiSede}.`) : null,
  );
}

// ---------------------------------------------------------------------
// Opiniones (MongoDB)
// ---------------------------------------------------------------------
const ORDENES = { recientes: "Más recientes", mejores: "Mejor calificadas", peores: "Peor calificadas", utiles: "Más útiles" };
const AJUSTES = { PEQUENA: "queda pequeña", EXACTA: "es exacta", GRANDE: "queda grande" };
const opiniones = { orden: "recientes", pagina: 1, items: [], total: 0 };

function textoAjuste(ajustes) {
  const partes = Object.entries(ajustes).sort((a, b) => b[1] - a[1])
    .map(([clave, n]) => `${n} ${n === 1 ? "dice" : "dicen"} que ${AJUSTES[clave] || clave.toLowerCase()}`);
  return partes.length ? `Sobre la talla: ${partes.join(", ")}.` : null;
}

function pintarResumen(resumen) {
  const zona = document.getElementById("resumen-opiniones");
  if (!resumen.total) {
    zona.replaceChildren(el("p", {}, "Todavía no hay opiniones de esta prenda. Si la tienes, cuéntanos cómo te quedó."));
    return;
  }
  const promedio = resumen.promedio.toLocaleString("es-CO", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  zona.replaceChildren(
    el("div", { class: "resumen" },
      el("p", { class: "resumen__nota" }, promedio,
        el("small", {}, `${resumen.total} ${resumen.total === 1 ? "opinión" : "opiniones"}`,
          resumen.compras_verificadas ? `, ${resumen.compras_verificadas} con compra verificada` : "")),
      el("ul", { class: "distribucion", "aria-label": "Opiniones por estrellas" },
        // Las claves numéricas de un objeto salen de menor a mayor: se ordenan de 5 a 1.
        Object.entries(resumen.distribucion).sort((a, b) => b[0] - a[0]).map(([n, cantidad]) =>
          el("li", {},
            el("span", {}, `${n}★`),
            el("span", { class: "distribucion__barra", "aria-hidden": "true" },
              el("span", { style: `width:${Math.round((cantidad / resumen.total) * 100)}%` })),
            el("span", {}, String(cantidad)))))),
    textoAjuste(resumen.ajuste_talla) ? el("p", { class: "ajuste" }, textoAjuste(resumen.ajuste_talla)) : null,
  );
}

function valorChip(valor) {
  if (typeof valor === "boolean") return valor ? "sí" : "no";
  return String(valor);
}

function tarjetaOpinion(r) {
  const comprada = r.talla ? `Compró talla ${r.talla}${r.color ? `, ${r.color}` : ""}` : null;
  const chips = [
    r.ajuste_talla ? `Talla: ${AJUSTES[r.ajuste_talla] || r.ajuste_talla}` : null,
    ...Object.entries(r.atributos || {}).map(([k, v]) => `${nombreAtributo(k)}: ${valorChip(v)}`),
  ].filter(Boolean);

  const boton = el("button", { class: "util", type: "button" }, `¿Te sirvió? Sí (${r.util})`);
  boton.addEventListener("click", async () => {
    boton.disabled = true;
    try {
      const { util } = await api(`/resenas/${r.id}/util`, { metodo: "POST" });
      boton.textContent = `Gracias por tu voto (${util})`;
    } catch {
      boton.disabled = false;
    }
  });

  return el("li", { class: "resena" },
    el("div", { class: "resena__cabeza" }, estrellas(r.calificacion),
      r.titulo ? el("p", { class: "resena__titulo" }, r.titulo) : null,
      r.compra_verificada ? el("span", { class: "verificada" }, "Compra verificada") : null),
    el("p", { class: "resena__meta" }, [r.autor.nombre, fecha(r.fecha), comprada].filter(Boolean).join(", ")),
    el("p", { class: "resena__texto" }, r.comentario),
    chips.length ? el("ul", { class: "resena__atributos" }, chips.map((c) => el("li", {}, c))) : null,
    r.fotos?.length ? el("p", { class: "resena__meta" }, r.fotos.map((url, i) =>
      [i ? " " : "", el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, `Ver foto ${i + 1}`)])) : null,
    (r.respuestas || []).map((resp) => el("div", { class: "respuesta-tienda" },
      el("strong", {}, `Respuesta de Solsticio, ${fecha(resp.fecha)}`), resp.texto)),
    boton,
  );
}

function pintarLista() {
  const lista = document.getElementById("lista-opiniones");
  const mas = document.getElementById("mas-opiniones");
  lista.replaceChildren(...opiniones.items.map(tarjetaOpinion));
  mas.replaceChildren(opiniones.items.length < opiniones.total
    ? el("button", { class: "boton boton--secundario", type: "button", onclick: () => cargarOpiniones(opiniones.pagina + 1) }, "Ver más opiniones")
    : "");
}

async function cargarOpiniones(pagina = 1) {
  const datos = await api(`/productos/${id}/resenas?orden=${opiniones.orden}&page=${pagina}&size=5`);
  opiniones.pagina = pagina;
  opiniones.total = datos.total;
  opiniones.items = pagina === 1 ? datos.items : opiniones.items.concat(datos.items);
  pintarResumen(datos.resumen);
  pintarLista();
}

function campo(etiquetaTexto, control, ayuda, ancho) {
  return el("div", { class: `campo${ancho ? " campo--ancho" : ""}` },
    el("label", { for: control.id }, etiquetaTexto), control, ayuda ? el("small", { id: `${control.id}-ayuda` }, ayuda) : null);
}

function formularioOpinion() {
  const variantes = producto.variantes.map((v) =>
    el("option", { value: v.id_variante }, `${v.talla}, ${v.color.nombre}`));
  const mensaje = el("p", { class: "mensaje-formulario", role: "status" });

  const form = el("form", { class: "formulario", id: "form-opinion", hidden: true, novalidate: true },
    el("div", { class: "campos" },
      campo("Tu nombre", el("input", { id: "op-nombre", name: "nombre", required: true, maxlength: 80, autocomplete: "name" })),
      campo("Tu correo", el("input", { id: "op-email", name: "email", type: "email", required: true, maxlength: 120, autocomplete: "email", "aria-describedby": "op-email-ayuda" }),
        "No se publica. Solo sirve para que cada persona opine una vez."),
      el("div", { class: "campo campo--ancho" },
        el("fieldset", {},
          el("legend", {}, "Calificación"),
          el("div", { class: "selector-estrellas" }, [1, 2, 3, 4, 5].map((n) =>
            el("label", {},
              el("input", { type: "radio", name: "calificacion", value: n, required: true, "aria-label": `${n} de 5` }),
              el("span", { "aria-hidden": "true" }, `${n}★`)))))),
      campo("Título (opcional)", el("input", { id: "op-titulo", name: "titulo", maxlength: 120 }), null, true),
      campo("Tu opinión", el("textarea", { id: "op-comentario", name: "comentario", required: true, maxlength: 2000 }), null, true),
      campo("Talla y color que compraste", el("select", { id: "op-variante", name: "id_variante" },
        el("option", { value: "" }, "Prefiero no decirlo"), variantes)),
      campo("¿Cómo te quedó?", el("select", { id: "op-ajuste", name: "ajuste_talla" },
        el("option", { value: "" }, "Prefiero no decirlo"),
        el("option", { value: "PEQUENA" }, "Me quedó pequeña"),
        el("option", { value: "EXACTA" }, "Me quedó exacta"),
        el("option", { value: "GRANDE" }, "Me quedó grande"))),
      campo("Código del pedido (opcional)", el("input", { id: "op-pedido", name: "codigo_pedido", maxlength: 80, placeholder: "SOL-P-00000001", "aria-describedby": "op-pedido-ayuda" }),
        "Si compraste en la web, con el código marcamos tu opinión como compra verificada.", true),
    ),
    el("div", { class: "formulario__acciones" },
      el("button", { class: "boton", type: "submit" }, "Publicar opinión"),
      el("button", { class: "boton boton--secundario", type: "button", onclick: () => { form.hidden = true; } }, "Cancelar")),
    mensaje,
  );

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const datos = Object.fromEntries(new FormData(form));
    const faltan = [];
    if (!datos.nombre?.trim()) faltan.push("tu nombre");
    if (!datos.email?.includes("@")) faltan.push("un correo válido");
    if (!datos.calificacion) faltan.push("la calificación");
    if (!datos.comentario?.trim()) faltan.push("tu opinión");
    if (faltan.length) {
      mensaje.className = "mensaje-formulario texto-no";
      mensaje.textContent = `Falta ${faltan.join(", ")}.`;
      return;
    }
    const cuerpo = { ...datos, calificacion: Number(datos.calificacion) };
    for (const clave of ["titulo", "id_variante", "ajuste_talla", "codigo_pedido"]) if (!cuerpo[clave]) delete cuerpo[clave];
    if (cuerpo.id_variante) cuerpo.id_variante = Number(cuerpo.id_variante);

    const boton = form.querySelector('button[type="submit"]');
    boton.disabled = true;
    try {
      await api(`/productos/${id}/resenas`, { metodo: "POST", cuerpo });
      form.reset();
      form.hidden = true;
      opiniones.orden = "recientes";
      document.getElementById("orden-opiniones").value = "recientes";
      await cargarOpiniones(1);
      document.getElementById("aviso-opinion").textContent = "Publicamos tu opinión. Gracias por contarnos.";
    } catch (error) {
      mensaje.className = "mensaje-formulario texto-no";
      mensaje.textContent = error.message;
    } finally {
      boton.disabled = false;
    }
  });
  return form;
}

function seccionOpiniones(datos) {
  if (!datos.nosql_disponible) {
    return el("section", { class: "resenas" }, el("h2", {}, "Opiniones"),
      el("div", { class: "aviso" }, el("p", {}, "Las opiniones no están disponibles en este momento. Vuelve a intentarlo más tarde.")));
  }
  const form = formularioOpinion();
  const orden = el("select", { id: "orden-opiniones", "aria-label": "Ordenar opiniones" },
    Object.entries(ORDENES).map(([valor, texto]) => el("option", { value: valor }, texto)));
  orden.addEventListener("change", () => { opiniones.orden = orden.value; cargarOpiniones(1).catch(() => {}); });

  return el("section", { class: "resenas", "aria-labelledby": "titulo-opiniones" },
    el("h2", { id: "titulo-opiniones" }, "Opiniones"),
    el("div", { id: "resumen-opiniones" }),
    el("div", { class: "controles-resenas" },
      orden,
      el("button", { class: "boton", type: "button", onclick: () => {
        form.hidden = false;
        form.querySelector("input").focus();
      } }, "Escribir una opinión")),
    el("p", { id: "aviso-opinion", class: "texto-si", role: "status" }),
    form,
    el("ul", { class: "lista-resenas", id: "lista-opiniones" }),
    el("div", { class: "mas", id: "mas-opiniones" }),
  );
}

// ---------------------------------------------------------------------
// Página
// ---------------------------------------------------------------------
function pintar(datos) {
  document.title = `${datos.nombre} | Solsticio`;
  document.getElementById("miga-actual").textContent = datos.nombre;
  const principal = datos.imagenes.find((i) => i.es_principal) || datos.imagenes[0];

  contenedor.replaceChildren(
    el("article", { class: "detalle" },
      el("div", { class: "detalle__foto" }, foto(principal?.url, datos.nombre)),
      el("div", {},
        el("p", { class: "detalle__categoria" }, datos.categoria.nombre),
        el("h1", { class: "detalle__nombre" }, datos.nombre),
        datos.descripcion ? el("p", { class: "detalle__descripcion" }, datos.descripcion) : null,
        datos.variantes.length
          ? el("div", { id: "zona-compra" })
          : el("div", { class: "aviso" }, el("p", {}, "Esta prenda todavía no tiene tallas a la venta.")))),
    el("div", { class: "debajo" },
      datos.ficha_tecnica ? etiqueta(datos.ficha_tecnica) : el("div"),
      seccionOpiniones(datos)),
  );

  if (datos.variantes.length) {
    elegirInicial();
    pintarCompra();
    document.getElementById("zona-compra").addEventListener("change", (evento) => {
      const { name, value } = evento.target;
      if (name === "talla") {
        seleccion.talla = value;
        const colores = coloresDe(value).map((v) => v.color.nombre);
        if (!colores.includes(seleccion.color)) seleccion.color = colores[0];
      } else if (name === "color") {
        seleccion.color = value;
      } else {
        return;
      }
      pintarCompra();
      document.querySelector(`#zona-compra input[name="${name}"][value="${CSS.escape(value)}"]`)?.focus();
    });
  }
  if (datos.nosql_disponible) {
    opiniones.items = datos.resenas.recientes;
    opiniones.total = datos.resenas.resumen.total;
    pintarResumen(datos.resenas.resumen);
    pintarLista();
  }
}

async function iniciar() {
  if (!id) {
    contenedor.replaceChildren(el("div", { class: "aviso" },
      el("p", {}, "No sabemos qué prenda quieres ver."), el("p", {}, el("a", { href: "/" }, "Volver al catálogo"))));
    return;
  }
  try {
    cabecera = await iniciarCabecera({ alCambiarSede: () => { if (producto?.variantes.length) pintarCompra(); } });
    producto = await api(`/productos/${id}/completo`);
    pintar(producto);
  } catch (error) {
    if (error.estado === 404) {
      contenedor.replaceChildren(el("div", { class: "aviso" },
        el("p", {}, "Esta prenda ya no está en el catálogo."), el("p", {}, el("a", { href: "/" }, "Ver el catálogo"))));
    } else {
      mostrarError(contenedor, error, iniciar);
    }
  }
}

iniciar();
