import unicodedata


def normalizar(texto: str) -> str:
    """Convierte a minúsculas y elimina diacríticos (tildes, diéresis, etc.)."""
    nfkd = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))
