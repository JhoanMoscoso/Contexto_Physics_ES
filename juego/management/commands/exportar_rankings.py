import csv
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from juego.embedding import Embedding
from juego.models import Target, Vocabulario


class Command(BaseCommand):
    help = (
        "Precalcula el ranking de todos los Target elegibles contra el "
        "vocabulario completo y lo exporta a CSV (uno por target + manifest.csv), "
        "para transferir a otro entorno sin que ese entorno tenga que recalcular. "
        "Carga el embedding una sola vez para toda la corrida."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            type=str,
            default="data/rankings_export",
            help="Directorio de salida para los CSV (default: data/rankings_export).",
        )
        parser.add_argument(
            "--forzar",
            action="store_true",
            help="Reprocesa también los targets que ya están disponible=True.",
        )
        parser.add_argument(
            "--todos",
            action="store_true",
            help="Incluye también targets sin ninguna pista válida (por defecto se excluyen).",
        )
        parser.add_argument(
            "--embedding-path",
            type=str,
            default=None,
            help="Ruta alternativa al .npz del embedding (default: settings.EMBEDDING_PATH).",
        )

    def handle(self, *args, **options):
        salida = Path(options["salida"])
        forzar = options["forzar"]
        todos = options["todos"]
        ruta_embedding = options["embedding_path"] or settings.EMBEDDING_PATH

        salida.mkdir(parents=True, exist_ok=True)

        qs = Target.objects.select_related("vocabulario").all()
        if not forzar:
            qs = qs.filter(disponible=False)
        if not todos:
            qs = [t for t in qs if t.pistas.count() > 0]
        else:
            qs = list(qs)

        if not qs:
            self.stdout.write(self.style.WARNING("No hay targets elegibles para exportar."))
            return

        self.stdout.write(f"Cargando embedding desde {ruta_embedding}...")
        t0 = time.monotonic()
        embedding = Embedding(ruta_embedding)
        t_carga = time.monotonic() - t0
        self.stdout.write(f"  ({t_carga:.2f}s)")

        total_embedding = len(embedding.id2word)
        total_vocab_bd = Vocabulario.objects.count()
        if total_vocab_bd != total_embedding:
            raise CommandError(
                f"Vocabulario en BD tiene {total_vocab_bd} palabras pero el "
                f"embedding tiene {total_embedding}. Desincronizado — abortando."
            )

        manifest_rows = []
        exportados = 0
        saltados_sin_palabra = 0

        for target in qs:
            palabra = target.palabra
            if palabra not in embedding.word2id:
                self.stdout.write(
                    self.style.WARNING(f"  [SKIP] '{palabra}' no está en el embedding.")
                )
                saltados_sin_palabra += 1
                continue

            idx_target = embedding.word2id[palabra]
            if embedding.id2word[target.vocabulario_id] != palabra:
                raise CommandError(
                    f"Desalineación detectada para '{palabra}': "
                    f"Vocabulario.id={target.vocabulario_id} no coincide con el embedding."
                )

            sims, ranks = embedding.ranking_completo(palabra)
            if ranks[idx_target] != 1:
                raise CommandError(
                    f"Verificación de sanidad falló para '{palabra}': rank propio "
                    f"= {ranks[idx_target]}, debería ser 1. Embedding sospechoso."
                )

            ruta_csv = salida / f"{target.vocabulario_id}.csv"
            with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for i in range(total_embedding):
                    writer.writerow([i, int(ranks[i]), round(float(sims[i]), 6)])

            manifest_rows.append((target.vocabulario_id, palabra, total_embedding))
            exportados += 1
            self.stdout.write(f"  [OK] {palabra} -> {ruta_csv.name} ({total_embedding} filas)")

        with open(salida / "manifest.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["vocabulario_id", "palabra", "n_filas"])
            writer.writerows(manifest_rows)

        self.stdout.write(self.style.SUCCESS("\n=== Resumen exportar_rankings ==="))
        self.stdout.write(f"  Targets exportados      : {exportados}")
        self.stdout.write(f"  Saltados (sin embedding): {saltados_sin_palabra}")
        self.stdout.write(f"  Directorio de salida    : {salida}")
        self.stdout.write(
            f"\nPara transferir: tar czf rankings.tar.gz -C {salida.parent} {salida.name}"
        )
