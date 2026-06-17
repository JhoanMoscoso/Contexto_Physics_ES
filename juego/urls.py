from django.urls import path

from . import views

urlpatterns = [
    path("target/actual", views.TargetActualView.as_view(), name="target-actual"),
    path("target/aleatorio", views.TargetAleatorioView.as_view(), name="target-aleatorio"),
    path("guess", views.GuessView.as_view(), name="guess"),
    path("pista", views.PistaView.as_view(), name="pista"),
]
