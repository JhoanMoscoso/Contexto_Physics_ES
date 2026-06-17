from django.db import models


class Vocabulario(models.Model):
    """Vocabulario completo del embedding. El id coincide con el índice de fila
    en la matriz de embeddings (Wn/vocab.npy), no es un autoincremental aparte."""

    id = models.PositiveIntegerField(primary_key=True)
    palabra = models.CharField(max_length=100, unique=True, db_index=True)
    palabra_normalizada = models.CharField(max_length=100, db_index=True, default="")
    frecuencia = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]
        verbose_name = "Vocabulario"
        verbose_name_plural = "Vocabulario"

    def __str__(self):
        return self.palabra


class Target(models.Model):
    TIPO_CHOICES = [
        ("sustantivo", "Sustantivo"),
        ("verbo", "Verbo"),
        ("nombre_propio", "Nombre propio"),
        ("unidad", "Unidad"),
        ("particula", "Partícula"),
        ("adjetivo", "Adjetivo"),
    ]

    vocabulario = models.OneToOneField(
        Vocabulario, on_delete=models.PROTECT, related_name="target"
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="sustantivo")
    activo = models.BooleanField(default=True)
    disponible = models.BooleanField(default=False)
    generado_en = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["vocabulario_id"]
        verbose_name = "Target"
        verbose_name_plural = "Targets"
        indexes = [
            models.Index(fields=["activo", "disponible"], name="idx_target_activo_disponible"),
        ]

    @property
    def palabra(self):
        return self.vocabulario.palabra

    def __str__(self):
        return f"{self.palabra} (vocab id {self.vocabulario_id})"


class Pista(models.Model):
    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name="pistas")
    orden = models.IntegerField()
    texto = models.TextField()

    class Meta:
        unique_together = ("target", "orden")
        ordering = ["orden"]
        verbose_name = "Pista"
        verbose_name_plural = "Pistas"

    def __str__(self):
        return f"Pista {self.orden} de {self.target.palabra}"


class RankingPalabra(models.Model):
    """Ranking precalculado de todo el vocabulario contra un Target.

    Generado offline por el comando `generar_juego`. Una fila por
    (target, palabra de vocabulario), con su similitud coseno y su
    rank (1 = más similar al target = la respuesta correcta).
    """

    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name="ranking")
    vocabulario = models.ForeignKey(Vocabulario, on_delete=models.CASCADE, related_name="+")
    rank = models.PositiveIntegerField()
    similitud = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["target", "vocabulario"], name="uq_ranking_target_vocab"
            ),
            models.UniqueConstraint(
                fields=["target", "rank"], name="uq_ranking_target_rank"
            ),
        ]
        indexes = [
            models.Index(fields=["target", "rank"]),
        ]
        verbose_name = "Ranking de palabra"
        verbose_name_plural = "Rankings de palabras"

    def __str__(self):
        return f"{self.target.palabra}: {self.vocabulario.palabra} (rank {self.rank})"
