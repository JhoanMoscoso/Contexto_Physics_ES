from django.apps import AppConfig


class JuegoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "juego"
    verbose_name = "Juego Contexto Física"

    def ready(self):
        from django.conf import settings
        from juego import embedding as emb_module
        from juego.embedding import Embedding

        if emb_module.EMBEDDING is None:
            emb_module.EMBEDDING = Embedding(settings.EMBEDDING_PATH)
