import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from juego.models import Pista, Target
from juego.utils import normalizar


class Command(BaseCommand):
    help = "Carga pistas.json en la tabla Pista con validación anti-spoiler (idempotente)."

    def handle(self, *args, **options):
        ruta = Path(__file__).resolve().parents[3] / "data" / "pistas.json"
        if not ruta.exists():
            self.stderr.write(f"No se encontró: {ruta}")
            return

        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)

        targets_procesados = 0
        pistas_creadas = 0
        pistas_existentes = 0
        pistas_rechazadas = 0
        targets_sin_registro = 0

        with transaction.atomic():
            for entrada in datos:
                palabra = entrada["palabra"]
                tipo = entrada.get("tipo", "sustantivo")
                pistas_raw = entrada.get("pistas", [])

                try:
                    target = Target.objects.get(palabra=palabra)
                except Target.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"  [SKIP] '{palabra}' no está en Target.")
                    )
                    targets_sin_registro += 1
                    continue

                target.tipo = tipo
                target.save(update_fields=["tipo"])
                targets_procesados += 1

                palabra_norm = normalizar(palabra)

                for orden, texto in enumerate(pistas_raw, start=1):
                    if palabra_norm in normalizar(texto):
                        self.stdout.write(
                            self.style.WARNING(
                                f"  [RECHAZADA] '{palabra}' pista {orden}: contiene la palabra objetivo."
                            )
                        )
                        pistas_rechazadas += 1
                        continue

                    _, created = Pista.objects.get_or_create(
                        target=target,
                        orden=orden,
                        defaults={"texto": texto},
                    )
                    if created:
                        pistas_creadas += 1
                    else:
                        pistas_existentes += 1

        self.stdout.write(self.style.SUCCESS("\n=== Resumen seed_pistas ==="))
        self.stdout.write(f"  Targets procesados  : {targets_procesados}")
        self.stdout.write(f"  Targets sin registro: {targets_sin_registro}")
        self.stdout.write(f"  Pistas creadas      : {pistas_creadas}")
        self.stdout.write(f"  Pistas ya existentes: {pistas_existentes}")
        if pistas_rechazadas:
            self.stdout.write(
                self.style.ERROR(f"  Pistas rechazadas   : {pistas_rechazadas}")
            )
        else:
            self.stdout.write(f"  Pistas rechazadas   : {pistas_rechazadas}")
