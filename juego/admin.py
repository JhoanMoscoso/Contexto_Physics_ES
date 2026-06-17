from django.contrib import admin

from .models import Pista, Target, Vocabulario


class PistaInline(admin.TabularInline):
    model = Pista
    extra = 1
    fields = ("orden", "texto")
    ordering = ("orden",)


@admin.register(Target)
class TargetAdmin(admin.ModelAdmin):
    list_display = (
        "palabra",
        "vocabulario",
        "tipo",
        "activo",
        "disponible",
        "generado_en",
        "creado",
    )
    list_filter = ("activo", "disponible", "tipo")
    search_fields = ("vocabulario__palabra",)
    list_editable = ("activo",)
    list_select_related = ("vocabulario",)
    inlines = [PistaInline]


@admin.register(Vocabulario)
class VocabularioAdmin(admin.ModelAdmin):
    list_display = ("id", "palabra", "frecuencia")
    search_fields = ("palabra",)
