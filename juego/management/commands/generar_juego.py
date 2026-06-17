import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from juego.embedding import Embedding
from juego.models import RankingPalabra, Target, Vocabulario


class Command(BaseCommand):
    help = (
        "Precalcula el ranking completo de una palabra Target contra todo el "
        "vocabulario y lo guarda en RankingPalabra. Carga el embedding solo "
        "durante esta corrida — el servidor web nunca lo necesita."
    )

    def add_arguments(self, parser):
        parser.add_argument("palabra", type=str)
        parser.add_argument(
            "--forzar",
            action="store_true",
            help="Si el target ya tiene ranking generado, lo borra y lo recalcula.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Tamaño de batch para la inserción masiva (default: 5000).",
        )
        parser.add_argument(
            "--embedding-path",
            type=str,
            default=None,
            help="Ruta alternativa al .npz del embedding (default: settings.EMBEDDING_PATH).",
        )

    def handle(self, *args, **options):
        palabra = options["palabra"].strip().lower()
        forzar = options["forzar"]
        batch_size = options["batch_size"]
        ruta_embedding = options["embedding_path"] or settings.EMBEDDING_PATH

        vocab_obj = Vocabulario.objects.filter(palabra=palabra).first()
        if vocab_obj is None:
            raise CommandError(
                f"La palabra '{palabra}' no está en Vocabulario. "
                "¿Está bien escrita? ¿Corriste seed_vocabulario?"
            )

        target = getattr(vocab_obj, "target", None)
        if target is None:
            raise CommandError(
                f"'{palabra}' no tiene un Target asociado. Creá el Target primero "
                "(admin o seed_targets) antes de generar su juego."
            )

        if target.disponible and not forzar:
            raise CommandError(
                f"'{palabra}' ya tiene un ranking generado el {target.generado_en}. "
                "Usá --forzar para regenerar."
            )

        self.stdout.write(f"Cargando embedding desde {ruta_embedding}...")
        t0 = time.monotonic()
        embedding = Embedding(ruta_embedding)
        t_carga = time.monotonic() - t0

        # Verificación de integridad: el Vocabulario en BD debe coincidir en
        # tamaño y, al menos en una muestra, en identidad con el embedding.
        total_embedding = len(embedding.id2word)
        total_vocab_bd = Vocabulario.objects.count()
        if total_vocab_bd != total_embedding:
            raise CommandError(
                f"Vocabulario en BD tiene {total_vocab_bd} palabras pero el "
                f"embedding tiene {total_embedding}. Desincronizado — abortando."
            )

        muestra_ids = {0, total_embedding - 1, vocab_obj.id}
        for vid in muestra_ids:
            v = Vocabulario.objects.get(id=vid)
            if v.palabra != embedding.id2word[vid]:
                raise CommandError(
                    f"Desalineación detectada: Vocabulario.id={vid} es '{v.palabra}' "
                    f"pero el embedding dice '{embedding.id2word[vid]}'. Abortando."
                )

        t0 = time.monotonic()
        sims, ranks = embedding.ranking_completo(palabra)
        t_calculo = time.monotonic() - t0

        idx_target = embedding.word2id[palabra]
        if ranks[idx_target] != 1:
            raise CommandError(
                f"Verificación de sanidad falló: el rank de '{palabra}' contra sí "
                f"misma es {ranks[idx_target]}, debería ser 1. Embedding sospechoso."
            )

        objetos = [
            RankingPalabra(
                target=target,
                vocabulario_id=i,
                rank=int(ranks[i]),
                similitud=float(sims[i]),
            )
            for i in range(total_embedding)
        ]

        filas_borradas = 0
        t0 = time.monotonic()
        with transaction.atomic():
            if target.disponible:
                filas_borradas = RankingPalabra.objects.filter(target=target).delete()[0]
            RankingPalabra.objects.bulk_create(objetos, batch_size=batch_size)
            target.disponible = True
            target.generado_en = timezone.now()
            target.save(update_fields=["disponible", "generado_en"])
        t_insercion = time.monotonic() - t0

        self.stdout.write(self.style.SUCCESS("\n=== Resumen generar_juego ==="))
        self.stdout.write(f"  Palabra             : {palabra}")
        self.stdout.write(f"  Vocabulario id      : {vocab_obj.id}")
        if filas_borradas:
            self.stdout.write(f"  Filas anteriores borradas: {filas_borradas}")
        self.stdout.write(f"  Filas insertadas    : {len(objetos)}")
        self.stdout.write(f"  Rank de sí misma    : {int(ranks[idx_target])} (OK)")
        self.stdout.write(f"  Tiempo de carga     : {t_carga:.2f}s")
        self.stdout.write(f"  Tiempo de cálculo   : {t_calculo:.2f}s")
        self.stdout.write(f"  Tiempo de inserción : {t_insercion:.2f}s")
        self.stdout.write(f"  Target.disponible   : True")
