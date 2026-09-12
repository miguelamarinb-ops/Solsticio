// catalogo.js — Lógica del catálogo virtual del Cliente (Solsticio)
// Consume la API Flask mediante fetch y renderiza las prendas dinámicamente.

const API_URL = "http://127.0.0.1:5000/api";

async function cargarFiltros() {
  const [categorias, sedes] = await Promise.all([
    fetch(`${API_URL}/categorias`).then(r => r.json()),
    fetch(`${API_URL}/sedes`).then(r => r.json())
  ]);

  const selectCategoria = document.getElementById("filtro-categoria");
  categorias.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.nombre;
    selectCategoria.appendChild(opt);
  });

  const selectSede = document.getElementById("filtro-sede");
  sedes.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.nombre;
    selectSede.appendChild(opt);
  });
}

function badgeStock(cantidad) {
  if (cantidad <= 0) return `<span class="stock-badge stock-agotado">Agotado</span>`;
  if (cantidad <= 5) return `<span class="stock-badge stock-bajo">Últimas ${cantidad} unidades</span>`;
  return `<span class="stock-badge stock-ok">${cantidad} disponibles</span>`;
}

async function cargarProductos() {
  const grid = document.getElementById("grid-productos");
  grid.innerHTML = `<p class="mensaje">Cargando catálogo...</p>`;

  const categoriaId = document.getElementById("filtro-categoria").value;
  const sedeId = document.getElementById("filtro-sede").value;

  let url = `${API_URL}/productos?`;
  if (categoriaId) url += `categoria_id=${categoriaId}&`;
  if (sedeId) url += `sede_id=${sedeId}&`;

  try {
    const respuesta = await fetch(url);
    if (!respuesta.ok) throw new Error("Error al consultar la API");
    const productos = await respuesta.json();

    if (productos.length === 0) {
      grid.innerHTML = `<p class="mensaje">No hay prendas disponibles con estos filtros.</p>`;
      return;
    }

    grid.innerHTML = "";
    productos.forEach(p => {
      const cantidadMostrada = sedeId ? p.stock_en_sede_consultada : p.stock_total;

      const listaStock = (p.stock_por_sede || [])
        .map(s => `<li>${s.sede}: ${s.cantidad} und.</li>`)
        .join("");

      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <img src="${p.imagen_url || 'https://via.placeholder.com/240x220?text=Solsticio'}" alt="${p.nombre}">
        <div class="card-body">
          <div class="categoria">${p.categoria || ''}</div>
          <h3>${p.nombre}</h3>
          <div class="precio">$${p.precio.toLocaleString('es-CO')}</div>
          ${badgeStock(cantidadMostrada)}
          <ul>${listaStock}</ul>
          <button onclick="verDetalle(${p.id})" ${cantidadMostrada <= 0 ? "disabled" : ""}>
            ${cantidadMostrada <= 0 ? "Sin stock" : "Ver / Comprar"}
          </button>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<p class="mensaje">No se pudo conectar con la tienda. Verifica que el backend Flask esté corriendo.</p>`;
    console.error(err);
  }
}

function verDetalle(productoId) {
  // Aquí se abriría un modal o se navegaría a /pedido con el producto seleccionado.
  alert("Producto seleccionado ID: " + productoId + "\n(Aquí se conectaría con POST /api/pedidos)");
}

document.getElementById("filtro-categoria").addEventListener("change", cargarProductos);
document.getElementById("filtro-sede").addEventListener("change", cargarProductos);

cargarFiltros().then(cargarProductos);