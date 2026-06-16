/* ── Estado ──────────────────────────────────────── */
const estado = {
  targetId: null,
  nPistas: 0,
  totalVocab: 0,
  intentos: [],       // [{palabra, rank, similitud}]
  pistasUsadas: 0,
  ganado: false,
};

/* ── Selectores ──────────────────────────────────── */
const formaGuess       = document.getElementById("forma-guess");
const inputPalabra     = document.getElementById("input-palabra");
const mensajeError     = document.getElementById("mensaje-error");
const listaIntentos    = document.getElementById("lista-intentos");
const contadorIntentos = document.getElementById("contador-intentos");
const contadorPistas   = document.getElementById("contador-pistas");
const btnPista         = document.getElementById("btn-pista");
const listaPistas      = document.getElementById("lista-pistas");
const bannerVictoria   = document.getElementById("banner-victoria");
const palabraRevelada  = document.getElementById("palabra-revelada");
const textoVictoria    = document.getElementById("texto-victoria");

/* ── Color y barra por ranking ───────────────────── */
function colorPorRank(rank) {
  if (rank === 1)    return "var(--verde-oscuro)";
  if (rank <= 100)   return "var(--verde-lima)";
  if (rank <= 300)   return "var(--turquesa)";
  if (rank <= 1000)  return "var(--verde-azulado)";
  return "var(--texto-suave)";
}

function anchoBarra(rank) {
  if (rank === 1) return "100%";
  const pct = Math.max(2, 100 - Math.log10(rank) * 25);
  return pct.toFixed(1) + "%";
}

/* ── Renderizado de un intento ───────────────────── */
function crearFilaIntento({ palabra, rank }) {
  const li = document.createElement("li");
  li.className = "intento-fila" + (rank === 1 ? " rank-ganador" : "");
  li.dataset.palabra = palabra;

  const color = colorPorRank(rank);
  const ancho = anchoBarra(rank);

  li.innerHTML = `
    <div class="intento-barra-wrap">
      <div class="intento-barra" style="width:${ancho};background:${color}"></div>
    </div>
    <span class="intento-palabra">${palabra}</span>
    <span class="intento-rank">#${rank}</span>
  `;
  return li;
}

/* ── Insertar intento en lista ordenada por rank asc */
function insertarIntento(intento) {
  const fila = crearFilaIntento(intento);
  const items = [...listaIntentos.querySelectorAll("li")];
  const siguiente = items.find(
    (li) => parseInt(li.querySelector(".intento-rank").textContent.slice(1)) > intento.rank
  );
  if (siguiente) {
    listaIntentos.insertBefore(fila, siguiente);
  } else {
    listaIntentos.appendChild(fila);
  }
}

/* ── Actualizar contadores en cabecera ───────────── */
function actualizarContadores() {
  const n = estado.intentos.length;
  contadorIntentos.textContent = `${n} intento${n !== 1 ? "s" : ""}`;
  contadorPistas.textContent   = `${estado.pistasUsadas} pista${estado.pistasUsadas !== 1 ? "s" : ""} usada${estado.pistasUsadas !== 1 ? "s" : ""}`;
}

/* ── Mostrar mensaje de error (temporal) ─────────── */
function mostrarError(msg) {
  mensajeError.textContent = msg;
  setTimeout(() => { mensajeError.textContent = ""; }, 4000);
}

/* ── Enviar intento ──────────────────────────────── */
formaGuess.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (estado.ganado) return;

  const palabra = inputPalabra.value.trim().toLowerCase();
  if (!palabra) return;

  // Deduplicar
  if (estado.intentos.find((i) => i.palabra === palabra)) {
    const filaExistente = listaIntentos.querySelector(`[data-palabra="${palabra}"]`);
    if (filaExistente) {
      filaExistente.classList.add("duplicado");
      setTimeout(() => filaExistente.classList.remove("duplicado"), 450);
    }
    inputPalabra.value = "";
    return;
  }

  const btn = formaGuess.querySelector("button");
  btn.disabled = true;

  try {
    const res = await fetch("/api/guess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_id: estado.targetId, palabra }),
    });
    const data = await res.json();

    if (!data.encontrada) {
      mostrarError("Esa palabra no está en el vocabulario. Prueba otra forma: singular/plural, infinitivo, etc.");
      inputPalabra.value = "";
      return;
    }

    const intento = { palabra: data.palabra, rank: data.rank, similitud: data.similitud };
    estado.intentos.push(intento);
    insertarIntento(intento);
    actualizarContadores();
    inputPalabra.value = "";

    if (data.ganaste) {
      estado.ganado = true;
      mostrarVictoria(data.palabra_secreta);
    }
  } catch {
    mostrarError("Error de conexión. Intenta de nuevo.");
  } finally {
    btn.disabled = false;
    inputPalabra.focus();
  }
});

/* ── Revelar pista ───────────────────────────────── */
btnPista.addEventListener("click", async () => {
  if (estado.ganado) return;
  const n = estado.pistasUsadas + 1;
  if (n > estado.nPistas) return;

  btnPista.disabled = true;

  try {
    const res = await fetch(`/api/pista?target_id=${estado.targetId}&n=${n}`);
    if (!res.ok) {
      mostrarError("No hay más pistas disponibles.");
      return;
    }
    const data = await res.json();
    estado.pistasUsadas = n;

    const li = document.createElement("li");
    li.textContent = data.texto;
    listaPistas.appendChild(li);

    actualizarContadores();

    if (estado.pistasUsadas >= estado.nPistas) {
      btnPista.disabled = true;
      btnPista.textContent = "Sin más pistas";
    } else {
      btnPista.disabled = false;
    }
  } catch {
    mostrarError("Error al cargar la pista.");
    btnPista.disabled = false;
  }
});

/* ── Banner de victoria ──────────────────────────── */
function mostrarVictoria(palabraSecreta) {
  const n = estado.intentos.length;
  palabraRevelada.textContent = palabraSecreta;
  textoVictoria.textContent   = `Lo encontraste en ${n} intento${n !== 1 ? "s" : ""}.`;
  bannerVictoria.hidden = false;
}

bannerVictoria.addEventListener("click", () => {
  bannerVictoria.hidden = true;
});

/* ── Inicialización ──────────────────────────────── */
async function init() {
  try {
    const res = await fetch("/api/target/actual");
    if (!res.ok) throw new Error("Sin target");
    const data = await res.json();

    estado.targetId   = data.target_id;
    estado.nPistas    = data.n_pistas;
    estado.totalVocab = data.total_vocab;

    if (estado.nPistas === 0) {
      btnPista.disabled = true;
      btnPista.textContent = "Sin pistas disponibles";
    }

    inputPalabra.focus();
  } catch {
    mostrarError("No se pudo cargar el juego. Recargá la página.");
  }
}

init();
