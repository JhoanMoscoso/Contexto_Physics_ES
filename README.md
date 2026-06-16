# Contexto Física

Juego tipo Contexto.me sobre vocabulario de física en español, basado en embeddings propios.

## Instalación local

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar entorno
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL y un SECRET_KEY aleatorio

# 4. Crear base de datos PostgreSQL
createdb contexto_fisica   # o crearla desde psql

# 5. Ejecutar migraciones
python manage.py migrate

# 6. Cargar datos
python manage.py seed_targets   # carga las ~300 palabras objetivo
python manage.py seed_pistas    # carga las pistas (con validación anti-spoiler)

# 7. Crear superusuario (opcional, para el admin)
python manage.py createsuperuser

# 8. Iniciar servidor
python manage.py runserver
```

Abrí `http://localhost:8000` en el navegador.

## Admin

`http://localhost:8000/admin/` — permite editar targets y pistas.

## Estructura de datos

- `data/embedding_fisica.npz`: vocabulario (~18 k palabras) y embeddings preentrenados
- `data/targets_contexto.csv`: ~300 palabras objetivo con rank y frecuencia
- `data/pistas.json`: pistas progresivas por palabra (de menos a más obvia)
