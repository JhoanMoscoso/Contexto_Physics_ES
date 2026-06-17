import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from juego.models import RankingPalabra, Target, Vocabulario


class Command(BaseCommand):
    help = (
        "Importa rankings precalculados (exportados con exportar_rankings) a este "
        "entorno, sin recalcular nada. Resuelve cada Target por vocabulario_id "
        "(palabra), nunca por el target_id crudo del entorno de origen — los IDs "
        "autoincrementales de Target no son estables entre entornos."
    )

    def add_arguments(self, parser):
        parser.add_argument("directorio", type=str)
        parser.add_argument(
            "--forzar",
            action="store_true",
            help="Si el target ya tiene ranking generado, lo borra y lo reemplaza.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Tamaño de batch para la inserción masiva (default: 5000).",
        )

    def handle(self, *args, **options):
        directorio = Path(options["directorio"])
        forzar = options["forzar"]
        batch_size = options["batch_size"]

        ruta_manifest = directorio / "manifest.csv"
        if not ruta_manifest.exists():
            raise CommandError(f"No se encontró manifest.csv en {directorio}")

        total_vocab_bd = Vocabulario.objects.count()

        with open(ruta_manifest, newline="", encoding="utf-8") as f:
            filas_manifest = list(csv.DictReader(f))

        importados = 0
        saltados_ya_disponible = 0
        saltados_sin_target = 0
        total_filas_importadas = 0

        for fila in filas_manifest:
            vocab_id = int(fila["vocabulario_id"])
            palabra = fila["palabra"]
            n_filas_esperadas = int(fila["n_filas"])

            target = Target.objects.select_related("vocabulario").filter(
                vocabulario_id=vocab_id
            ).first()
            if target is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [SKIP] No existe Target para vocabulario_id={vocab_id} "
                        f"('{palabra}') en este entorno."
                    )
                )
                saltados_sin_target += 1
                continue

            if target.palabra != palabra:
                raise CommandError(
                    f"Desalineación: vocabulario_id={vocab_id} es '{target.palabra}' "
                    f"en este entorno, pero el manifest dice '{palabra}'. Abortando."
                )

            if target.disponible and not forzar:
                self.stdout.write(
                    self.style.WARNING(f"  [SKIP] '{palabra}' ya disponible (usá --forzar).")
                )
                saltados_ya_disponible += 1
                continue

            ruta_csv = directorio / f"{vocab_id}.csv"
            if not ruta_csv.exists():
                raise CommandError(f"Falta el archivo {ruta_csv} listado en el manifest.")

            with open(ruta_csv, newline="", encoding="utf-8") as f:
                filas = [
                    (int(r[0]), int(r[1]), float(r[2])) for r in csv.reader(f)
                ]

            if len(filas) != total_vocab_bd or len(filas) != n_filas_esperadas:
                raise CommandError(
                    f"'{palabra}': el CSV tiene {len(filas)} filas, se esperaban "
                    f"{n_filas_esperadas} (manifest) / {total_vocab_bd} (Vocabulario "
                    "de este entorno). Archivo incompleto o vocabulario desincronizado."
                )

            objetos = [
                RankingPalabra(target=target, vocabulario_id=vid, rank=rank, similitud=sim)
                for vid, rank, sim in filas
            ]

            with transaction.atomic():
                if target.disponible:
                    RankingPalabra.objects.filter(target=target).delete()
                RankingPalabra.objects.bulk_create(objetos, batch_size=batch_size)
                target.disponible = True
                target.generado_en = timezone.now()
                target.save(update_fields=["disponible", "generado_en"])

            importados += 1
            total_filas_importadas += len(objetos)
            self.stdout.write(f"  [OK] {palabra} ({len(objetos)} filas)")

        self.stdout.write(self.style.SUCCESS("\n=== Resumen importar_rankings ==="))
        self.stdout.write(f"  Targets importados        : {importados}")
        self.stdout.write(f"  Filas totales importadas   : {total_filas_importadas}")
        self.stdout.write(f"  Saltados (ya disponibles)  : {saltados_ya_disponible}")
        self.stdout.write(f"  Saltados (sin Target aquí) : {saltados_sin_target}")
