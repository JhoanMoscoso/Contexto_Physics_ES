import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from juego.models import Pista, Target
from juego.utils import normalizar


class Command(BaseCommand):
    help = "Limpia y reinserta Pista desde data/pistas.json con validación anti-spoiler."

    def handle(self, *args, **options):
        ruta = Path(__file__).resolve().parents[3] / "data" / "pistas.json"
        if not ruta.exists():
            self.stderr.write(f"No se encontró: {ruta}")
            return

        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)

        targets_por_palabra = {
            t.palabra: t for t in Target.objects.select_related("vocabulario").all()
        }

        targets_procesados = 0
        targets_sin_registro = 0
        pistas_rechazadas = 0
        nuevas_pistas = []
        targets_a_actualizar = []

        for entrada in datos:
            palabra = entrada["palabra"]
            tipo = entrada.get("tipo", "sustantivo")
            pistas_raw = entrada.get("pistas", [])

            target = targets_por_palabra.get(palabra)
            if target is None:
                self.stdout.write(
                    self.style.WARNING(f"  [SKIP] '{palabra}' no está en Target.")
                )
                targets_sin_registro += 1
                continue

            target.tipo = tipo
            targets_a_actualizar.append(target)
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

                nuevas_pistas.append(Pista(target=target, orden=orden, texto=texto))

        with transaction.atomic():
            Pista.objects.all().delete()
            Target.objects.bulk_update(targets_a_actualizar, ["tipo"])
            Pista.objects.bulk_create(nuevas_pistas)

        self.stdout.write(self.style.SUCCESS("\n=== Resumen seed_pistas ==="))
        self.stdout.write(f"  Targets procesados  : {targets_procesados}")
        self.stdout.write(f"  Targets sin registro: {targets_sin_registro}")
        self.stdout.write(f"  Pistas creadas      : {len(nuevas_pistas)}")
        if pistas_rechazadas:
            self.stdout.write(
                self.style.ERROR(f"  Pistas rechazadas   : {pistas_rechazadas}")
            )
        else:
            self.stdout.write(f"  Pistas rechazadas   : {pistas_rechazadas}")
