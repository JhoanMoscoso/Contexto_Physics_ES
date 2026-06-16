from django.db import models


class Target(models.Model):
    TIPO_CHOICES = [
        ("sustantivo", "Sustantivo"),
        ("verbo", "Verbo"),
        ("nombre_propio", "Nombre propio"),
        ("unidad", "Unidad"),
        ("particula", "Partícula"),
        ("adjetivo", "Adjetivo"),
    ]

    palabra = models.CharField(max_length=100, unique=True, db_index=True)
    rank = models.IntegerField()
    frecuencia = models.IntegerField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="sustantivo")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["rank"]
        verbose_name = "Target"
        verbose_name_plural = "Targets"

    def __str__(self):
        return f"{self.palabra} (rank {self.rank})"


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
