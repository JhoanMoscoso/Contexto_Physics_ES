import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from juego.models import Vocabulario
from juego.utils import normalizar


class Command(BaseCommand):
    help = "Limpia y reinserta el vocabulario completo desde data/vocabulario.csv."

    def handle(self, *args, **options):
        ruta = Path(__file__).resolve().parents[3] / "data" / "vocabulario.csv"
        if not ruta.exists():
            self.stderr.write(f"No se encontró: {ruta}")
            return

        with open(ruta, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            filas = [
                Vocabulario(
                    id=int(row["rank"]),
                    palabra=row["palabra"],
                    palabra_normalizada=normalizar(row["palabra"]),
                    frecuencia=int(row["frecuencia"]),
                )
                for row in reader
            ]

        Vocabulario.objects.all().delete()
        Vocabulario.objects.bulk_create(filas, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(f"seed_vocabulario: {len(filas)} palabras insertadas.")
        )
