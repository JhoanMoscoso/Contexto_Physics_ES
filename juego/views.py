import random
from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pista, RankingPalabra, Target, Vocabulario
from .serializers import GuessInputSerializer, PistaQuerySerializer, PistaSerializer
from .utils import normalizar


def _resolver_vocabulario(palabra: str):
    """Resuelve una palabra escrita por el jugador a su fila de Vocabulario.

    Siempre busca por forma normalizada (sin tildes) primero. Si hay un solo
    candidato, no hay ambigüedad. Si hay más de uno (colisión real, ej.
    "electron"/"electrón"):
    - si el usuario escribió alguna tilde (señal deliberada), se prioriza el
      candidato cuyo `palabra` coincide exactamente con lo que escribió;
    - si no escribió ninguna tilde, no hay forma de saber cuál quiso decir
      por la ortografía sola, así que se desambigua por la palabra con mayor
      frecuencia en el corpus (la interpretación más probable).
    Devuelve None si la palabra no existe en el vocabulario de ninguna forma.
    """
    palabra_norm = normalizar(palabra)
    candidatos = list(Vocabulario.objects.filter(palabra_normalizada=palabra_norm))
    if not candidatos:
        return None
    if len(candidatos) == 1:
        return candidatos[0]

    tiene_tilde = palabra != palabra_norm
    if tiene_tilde:
        exacto = next((c for c in candidatos if c.palabra == palabra), None)
        if exacto is not None:
            return exacto

    return max(candidatos, key=lambda v: v.frecuencia)


class TargetActualView(APIView):
    """Devuelve el target activo y disponible del día, sin revelar la palabra."""

    def get(self, request):
        qs = (
            Target.objects.select_related("vocabulario")
            .filter(activo=True, disponible=True)
            .order_by("id")
        )
        count = qs.count()
        if count == 0:
            return Response({"error": "No hay targets disponibles."}, status=503)
        idx = date.today().toordinal() % count
        target = qs[idx]
        return Response(
            {
                "target_id": target.pk,
                "total_vocab": Vocabulario.objects.count(),
                "n_pistas": target.pistas.count(),
            }
        )


class TargetAleatorioView(APIView):
    """Devuelve un target aleatorio entre los disponibles, excluyendo opcionalmente uno."""

    def get(self, request):
        excluir_id = request.query_params.get("excluir")
        qs = Target.objects.select_related("vocabulario").filter(
            activo=True, disponible=True
        )
        if excluir_id:
            qs = qs.exclude(pk=excluir_id)
        count = qs.count()
        if count == 0:
            return Response({"error": "No hay otros targets disponibles."}, status=503)
        target = qs[random.randrange(count)]
        return Response(
            {
                "target_id": target.pk,
                "total_vocab": Vocabulario.objects.count(),
                "n_pistas": target.pistas.count(),
            }
        )


class GuessView(APIView):
    """Evalúa un intento del jugador contra el ranking precalculado."""

    def post(self, request):
        serializer = GuessInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        target_id = serializer.validated_data["target_id"]
        palabra = serializer.validated_data["palabra"]

        target = get_object_or_404(
            Target.objects.select_related("vocabulario"),
            pk=target_id,
            activo=True,
            disponible=True,
        )

        vocab_obj = _resolver_vocabulario(palabra)
        if vocab_obj is None:
            return Response({"encontrada": False})

        fila = RankingPalabra.objects.filter(
            target=target, vocabulario_id=vocab_obj.id
        ).first()
        if fila is None:
            return Response({"encontrada": False})

        rank, similitud = fila.rank, fila.similitud
        ganaste = rank == 1
        respuesta = {
            "encontrada": True,
            "palabra": vocab_obj.palabra,
            "rank": rank,
            "similitud": round(similitud, 6),
            "ganaste": ganaste,
        }
        if ganaste:
            respuesta["palabra_secreta"] = target.palabra
        return Response(respuesta)


class PistaView(APIView):
    """Devuelve la pista de orden n para el target dado."""

    def get(self, request):
        serializer = PistaQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        target_id = serializer.validated_data["target_id"]
        n = serializer.validated_data["n"]

        target = get_object_or_404(Target, pk=target_id, activo=True, disponible=True)
        pista = get_object_or_404(Pista, target=target, orden=n)
        return Response(PistaSerializer(pista).data)
