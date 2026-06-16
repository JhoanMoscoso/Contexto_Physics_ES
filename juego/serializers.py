from rest_framework import serializers

from .models import Pista


class GuessInputSerializer(serializers.Serializer):
    target_id = serializers.IntegerField()
    palabra = serializers.CharField(max_length=100)

    def validate_palabra(self, value):
        return value.strip().lower()


class PistaQuerySerializer(serializers.Serializer):
    target_id = serializers.IntegerField()
    n = serializers.IntegerField(min_value=1)


class PistaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pista
        fields = ("orden", "texto")
