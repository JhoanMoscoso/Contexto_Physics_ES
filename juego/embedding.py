import numpy as np


class Embedding:
    """Word embedding en memoria con cálculo de ranking por similitud coseno.

    Las filas de Wn están normalizadas a norma 1, por lo que el coseno
    es directamente el producto punto: similitud = Wn @ vector_target.
    """

    def __init__(self, ruta):
        datos = np.load(ruta, allow_pickle=False)
        self.id2word = [str(w) for w in datos["vocab"]]
        self.word2id = {w: i for i, w in enumerate(self.id2word)}
        self.Wn = datos["Wn"].astype(np.float32)
        self._cache: dict = {}

    def _sims(self, target: str) -> np.ndarray:
        """Vector de similitudes coseno del target con todo el vocabulario (cacheado)."""
        if target not in self._cache:
            self._cache[target] = self.Wn @ self.Wn[self.word2id[target]]
        return self._cache[target]

    def evaluar(self, target: str, guess: str):
        """Devuelve (rank, similitud) del guess respecto al target, o None si es OOV.

        rank = número de palabras estrictamente más similares + 1.
        rank == 1 significa que guess es el vecino más cercano al target.
        """
        if guess not in self.word2id or target not in self.word2id:
            return None
        sims = self._sims(target)
        sim_guess = float(sims[self.word2id[guess]])
        rank = int((sims > sim_guess).sum()) + 1
        return rank, sim_guess

    def ranking_completo(self, target: str):
        """Devuelve (sims, ranks) para TODO el vocabulario respecto al target.

        ranks[i] es el rank de la palabra de índice i (1 = más similar).
        Pensado para un cálculo único por target (no usa el cache de _sims
        más allá de esta sola llamada).
        """
        if target not in self.word2id:
            raise KeyError(target)
        sims = self._sims(target)
        orden_desc = np.argsort(-sims)
        ranks = np.empty_like(orden_desc)
        ranks[orden_desc] = np.arange(1, len(sims) + 1)
        return sims, ranks

    @property
    def total_vocab(self) -> int:
        return len(self.id2word)
