import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from juego.models import Target, Vocabulario


class Command(BaseCommand):
    help = "Carga targets_contexto.csv en la tabla Target con FK a Vocabulario (idempotente)."

    def handle(self, *args, **options):
        ruta = Path(__file__).resolve().parents[3] / "data" / "targets_contexto.csv"
        if not ruta.exists():
            self.stderr.write(f"No se encontró: {ruta}")
            return

        with open(ruta, newline="", encoding="utf-8") as f:
            filas = list(csv.DictReader(f))

        palabras = [row["palabra"] for row in filas]
        vocab_map = dict(
            Vocabulario.objects.filter(palabra__in=palabras).values_list("palabra", "id")
        )

        creados = 0
        actualizados = 0
        sin_vocabulario = 0

        for row in filas:
            vocab_id = vocab_map.get(row["palabra"])
            if vocab_id is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [SKIP] '{row['palabra']}' no está en Vocabulario "
                        "(¿corriste seed_vocabulario?)."
                    )
                )
                sin_vocabulario += 1
                continue

            _, created = Target.objects.update_or_create(vocabulario_id=vocab_id)
            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_targets: {creados} creados, {actualizados} actualizados, "
                f"{sin_vocabulario} sin registro en Vocabulario."
            )
        )
