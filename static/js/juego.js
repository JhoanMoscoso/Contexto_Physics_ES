/* ── Estado ──────────────────────────────────────── */
const estado = {
  targetId: null,
  nPistas: 0,
  totalVocab: 0,
  intentos: [],       // [{palabra, rank, similitud}]
  pistasUsadas: 0,
  pistasDesbloqueadas: 0,
  inicioJuego: null,
  tiempoFinal: null,
  ganado: false,
};

const UMBRALES_PISTA = [60, 180, 300, 480]; // segundos para desbloquear pista 1, 2, 3, 4
let intervalTimer = null;

/* ── Selectores ──────────────────────────────────── */
const formaGuess           = document.getElementById("forma-guess");
const inputPalabra         = document.getElementById("input-palabra");
const mensajeError         = document.getElementById("mensaje-error");
const listaIntentos        = document.getElementById("lista-intentos");
const contadorIntentos     = document.getElementById("contador-intentos");
const contadorPistas       = document.getElementById("contador-pistas");
const contadorTimer        = document.getElementById("contador-timer");
const btnPista              = document.getElementById("btn-pista");
const listaPistas          = document.getElementById("lista-pistas");
const bannerVictoria       = document.getElementById("banner-victoria");
const palabraRevelada      = document.getElementById("palabra-revelada");
const textoLogro           = document.getElementById("texto-logro");
const textoVictoria        = document.getElementById("texto-victoria");
const btnNuevoJuego        = document.getElementById("btn-nuevo-juego");
const modalNuevoJuego      = document.getElementById("modal-nuevo-juego");
const btnCancelarNuevoJuego  = document.getElementById("btn-cancelar-nuevo-juego");
const btnConfirmarNuevoJuego = document.getElementById("btn-confirmar-nuevo-juego");
const btnAdivinar           = formaGuess.querySelector("button");
const seccionStatsVictoria  = document.getElementById("seccion-stats-victoria");
const statsTiempo           = document.getElementById("stats-tiempo");
const statsPistas           = document.getElementById("stats-pistas");
const btnJugarDeNuevo       = document.getElementById("btn-jugar-de-nuevo");

const vistaLobby            = document.getElementById("vista-lobby");
const vistaInstrucciones    = document.getElementById("vista-instrucciones");
const vistaJuego            = document.getElementById("vista-juego");
const btnJugar               = document.getElementById("btn-jugar");
const btnInstrucciones       = document.getElementById("btn-instrucciones");
const btnVolverLobby         = document.getElementById("btn-volver-lobby");
const btnJugarDesdeInstrucciones = document.getElementById("btn-jugar-desde-instrucciones");

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
  return fila;
}

/* ── Resaltar el último intento adivinado ────────── */
function marcarUltimoIntento(fila) {
  const anterior = listaIntentos.querySelector(".ultimo-intento");
  if (anterior) anterior.classList.remove("ultimo-intento");
  fila.classList.add("ultimo-intento");
}

/* ── Actualizar contadores en cabecera ───────────── */
function actualizarContadores() {
  const n = estado.intentos.length;
  contadorIntentos.textContent = `${n} intento${n !== 1 ? "s" : ""}`;
  contadorPistas.textContent   = `${estado.pistasUsadas} pista${estado.pistasUsadas !== 1 ? "s" : ""} usada${estado.pistasUsadas !== 1 ? "s" : ""}`;
}

/* ── Normalización para comparar duplicados sin tildes ── */
function normalizarJS(texto) {
  return texto.normalize("NFD").replace(new RegExp("[\\u0300-\\u036f]", "g"), "").toLowerCase();
}

/* ── Mostrar mensaje de error (temporal, visible en cualquier vista) ── */
function mostrarError(msg) {
  mensajeError.textContent = msg;
  mensajeError.hidden = false;
  setTimeout(() => {
    mensajeError.hidden = true;
    mensajeError.textContent = "";
  }, 4000);
}

/* ── Timer de desbloqueo de pistas ────────────────── */
function formatTiempo(segundos) {
  const m = Math.floor(segundos / 60);
  const s = segundos % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function actualizarEstadoBotonPista(transcurrido) {
  if (estado.ganado) {
    btnPista.disabled = true;
    return;
  }

  if (estado.pistasUsadas >= estado.nPistas) {
    btnPista.disabled = true;
    btnPista.textContent = estado.nPistas === 0 ? "Sin pistas disponibles" : "Sin más pistas";
    return;
  }

  const siguienteOrden = estado.pistasUsadas + 1;
  if (siguienteOrden > estado.pistasDesbloqueadas) {
    const umbral = UMBRALES_PISTA[siguienteOrden - 1];
    const faltan = Math.max(0, umbral - transcurrido);
    btnPista.disabled = true;
    btnPista.textContent = `Próxima pista en ${formatTiempo(faltan)}`;
  } else {
    btnPista.disabled = false;
    btnPista.textContent = "Revelar pista";
  }
}

function actualizarTimer() {
  const transcurrido = Math.floor((Date.now() - estado.inicioJuego) / 1000);
  contadorTimer.textContent = formatTiempo(transcurrido);
  estado.pistasDesbloqueadas = UMBRALES_PISTA.filter((u) => transcurrido >= u).length;
  actualizarEstadoBotonPista(transcurrido);

  if (estado.ganado || estado.pistasDesbloqueadas >= UMBRALES_PISTA.length) {
    detenerTimer();
  }
}

function iniciarTimer() {
  detenerTimer();
  estado.inicioJuego = Date.now();
  estado.pistasDesbloqueadas = 0;
  actualizarTimer();
  intervalTimer = setInterval(actualizarTimer, 1000);
}

function detenerTimer() {
  if (intervalTimer) {
    clearInterval(intervalTimer);
    intervalTimer = null;
  }
}

/* ── Enviar intento ──────────────────────────────── */
formaGuess.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (estado.ganado) return;

  const palabra = inputPalabra.value.trim().toLowerCase();
  if (!palabra) return;

  // Deduplicar (comparando sin tildes, ya que el servidor puede resolver
  // distintas formas tildadas/no tildadas a la misma palabra canónica)
  const palabraNorm = normalizarJS(palabra);
  const existente = estado.intentos.find((i) => normalizarJS(i.palabra) === palabraNorm);
  if (existente) {
    const filaExistente = listaIntentos.querySelector(`[data-palabra="${existente.palabra}"]`);
    if (filaExistente) {
      filaExistente.classList.add("duplicado");
      setTimeout(() => filaExistente.classList.remove("duplicado"), 450);
    }
    inputPalabra.value = "";
    return;
  }

  btnAdivinar.disabled = true;

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
    const fila = insertarIntento(intento);
    marcarUltimoIntento(fila);
    actualizarContadores();
    inputPalabra.value = "";

    if (data.ganaste) {
      estado.ganado = true;
      mostrarVictoria(data.palabra_secreta);
    }
  } catch {
    mostrarError("Error de conexión. Intenta de nuevo.");
  } finally {
    if (!estado.ganado) btnAdivinar.disabled = false;
    inputPalabra.focus();
  }
});

/* ── Revelar pista ───────────────────────────────── */
btnPista.addEventListener("click", async () => {
  if (estado.ganado) return;
  const n = estado.pistasUsadas + 1;
  if (n > estado.nPistas || n > estado.pistasDesbloqueadas) return;

  btnPista.disabled = true;

  const transcurrido = Math.floor((Date.now() - estado.inicioJuego) / 1000);

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
  } catch {
    mostrarError("Error al cargar la pista.");
  } finally {
    actualizarEstadoBotonPista(transcurrido);
  }
});

/* ── Banner de victoria ──────────────────────────── */
function mostrarVictoria(palabraSecreta) {
  estado.tiempoFinal = Math.floor((Date.now() - estado.inicioJuego) / 1000);
  detenerTimer();
  const n = estado.intentos.length;
  palabraRevelada.textContent = palabraSecreta;

  let logro;
  if (estado.pistasUsadas === 0) {
    logro = "Felicidades, lograste adivinar la palabra solo usando sus similaridades semánticas!";
  } else if (estado.pistasUsadas === 1) {
    logro = "Felicidades, lograste adivinar la palabra usando solo una pista";
  } else {
    logro = "Felicidades, adivinaste la palabra!";
  }
  textoLogro.textContent = logro;
  textoVictoria.textContent = `Lo encontraste en ${n} intento${n !== 1 ? "s" : ""}.`;
  bannerVictoria.hidden = false;
}

/* ── Cuadro de stats al cerrar el banner de victoria ── */
function mostrarStatsVictoria() {
  statsTiempo.textContent = formatTiempo(estado.tiempoFinal);
  statsPistas.textContent = `${estado.pistasUsadas} pista${estado.pistasUsadas !== 1 ? "s" : ""}`;
  seccionStatsVictoria.hidden = false;
  inputPalabra.disabled = true;
  btnAdivinar.disabled = true;
}

bannerVictoria.addEventListener("click", () => {
  bannerVictoria.hidden = true;
  mostrarStatsVictoria();
});

/* ── Nuevo juego (botón de dado) ───────────────────── */
btnNuevoJuego.addEventListener("click", () => {
  if (estado.ganado) {
    solicitarNuevoJuego();
    return;
  }
  modalNuevoJuego.hidden = false;
});

btnCancelarNuevoJuego.addEventListener("click", () => {
  modalNuevoJuego.hidden = true;
});

modalNuevoJuego.addEventListener("click", (e) => {
  if (e.target === modalNuevoJuego) modalNuevoJuego.hidden = true;
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalNuevoJuego.hidden) modalNuevoJuego.hidden = true;
});

btnConfirmarNuevoJuego.addEventListener("click", () => {
  modalNuevoJuego.hidden = true;
  solicitarNuevoJuego();
});

async function solicitarNuevoJuego() {
  try {
    const data = await cargarTarget(`/api/target/aleatorio?excluir=${estado.targetId}`);
    aplicarTarget(data);
  } catch (err) {
    mostrarError(err.message || "No hay más juegos disponibles todavía. ¡Volvé más tarde!");
  }
}

/* ── Carga e inicialización ──────────────────────── */
async function cargarTarget(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || "No se pudo cargar el juego.");
  }
  return res.json();
}

function limpiarUI() {
  listaIntentos.innerHTML = "";
  listaPistas.innerHTML = "";
  mensajeError.textContent = "";
  mensajeError.hidden = true;
  bannerVictoria.hidden = true;
  seccionStatsVictoria.hidden = true;
  inputPalabra.disabled = false;
  btnAdivinar.disabled = false;
  inputPalabra.value = "";
}

function aplicarTarget(data) {
  detenerTimer(); // reset explícito del timer de pistas entre juegos
  limpiarUI();

  estado.targetId = data.target_id;
  estado.nPistas = data.n_pistas;
  estado.totalVocab = data.total_vocab;
  estado.intentos = [];
  estado.pistasUsadas = 0;
  estado.tiempoFinal = null;
  estado.ganado = false;

  actualizarContadores();
  iniciarTimer();

  inputPalabra.focus();
}

/* ── Navegación entre vistas (lobby / instrucciones / juego) ── */
function mostrarLobby() {
  vistaLobby.hidden = false;
  vistaInstrucciones.hidden = true;
  vistaJuego.hidden = true;
}

function mostrarInstrucciones() {
  vistaLobby.hidden = true;
  vistaInstrucciones.hidden = false;
  vistaJuego.hidden = true;
}

function mostrarVistaJuego() {
  vistaLobby.hidden = true;
  vistaInstrucciones.hidden = true;
  vistaJuego.hidden = false;
}

async function jugar() {
  try {
    const data = await cargarTarget("/api/target/aleatorio");
    mostrarVistaJuego();
    aplicarTarget(data);
  } catch {
    mostrarError("No se pudo cargar el juego. Intentá de nuevo.");
  }
}

btnJugar.addEventListener("click", jugar);
btnJugarDesdeInstrucciones.addEventListener("click", jugar);
btnInstrucciones.addEventListener("click", mostrarInstrucciones);
btnVolverLobby.addEventListener("click", mostrarLobby);
btnJugarDeNuevo.addEventListener("click", solicitarNuevoJuego);

function init() {
  mostrarLobby();
}

init();
