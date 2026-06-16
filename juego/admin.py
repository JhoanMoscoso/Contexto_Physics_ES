from django.contrib import admin

from .models import Pista, Target


class PistaInline(admin.TabularInline):
    model = Pista
    extra = 1
    fields = ("orden", "texto")
    ordering = ("orden",)


@admin.register(Target)
class TargetAdmin(admin.ModelAdmin):
    list_display = ("palabra", "rank", "frecuencia", "tipo", "activo", "creado")
    list_filter = ("activo", "tipo")
    search_fields = ("palabra",)
    list_editable = ("activo",)
    inlines = [PistaInline]
