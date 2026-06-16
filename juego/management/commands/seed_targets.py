import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from juego.models import Target


class Command(BaseCommand):
    help = "Carga targets_contexto.csv en la tabla Target (idempotente)."

    def handle(self, *args, **options):
        ruta = Path(__file__).resolve().parents[3] / "data" / "targets_contexto.csv"
        if not ruta.exists():
            self.stderr.write(f"No se encontró: {ruta}")
            return

        creados = 0
        actualizados = 0

        with open(ruta, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                _, created = Target.objects.update_or_create(
                    palabra=row["palabra"],
                    defaults={
                        "rank": int(row["rank"]),
                        "frecuencia": int(row["frecuencia"]),
                    },
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_targets: {creados} creados, {actualizados} actualizados."
            )
        )
