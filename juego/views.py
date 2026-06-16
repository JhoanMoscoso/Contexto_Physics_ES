from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from juego import embedding as emb_module

from .models import Pista, Target
from .serializers import GuessInputSerializer, PistaQuerySerializer, PistaSerializer


class TargetActualView(APIView):
    """Devuelve el target activo del día sin revelar la palabra."""

    def get(self, request):
        qs = Target.objects.filter(activo=True).order_by("id")
        count = qs.count()
        if count == 0:
            return Response({"error": "No hay targets activos."}, status=503)
        idx = date.today().toordinal() % count
        target = qs[idx]
        return Response(
            {
                "target_id": target.pk,
                "total_vocab": emb_module.EMBEDDING.total_vocab,
                "n_pistas": target.pistas.count(),
            }
        )


class GuessView(APIView):
    """Evalúa un intento del jugador."""

    def post(self, request):
        serializer = GuessInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        target_id = serializer.validated_data["target_id"]
        palabra = serializer.validated_data["palabra"]

        target = get_object_or_404(Target, pk=target_id, activo=True)

        resultado = emb_module.EMBEDDING.evaluar(target.palabra, palabra)
        if resultado is None:
            return Response({"encontrada": False})

        rank, similitud = resultado
        ganaste = rank == 1
        respuesta = {
            "encontrada": True,
            "palabra": palabra,
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

        target = get_object_or_404(Target, pk=target_id, activo=True)
        pista = get_object_or_404(Pista, target=target, orden=n)
        return Response(PistaSerializer(pista).data)
