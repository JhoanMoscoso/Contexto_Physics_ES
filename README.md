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
# Editar .env con un SECRET_KEY aleatorio.
# Por defecto usa SQLite (no requiere configurar nada más).
# Para usar PostgreSQL, definir ENVIRONMENT_TYPE=PRODUCTION y las variables DB_*.

# 4. Si ENVIRONMENT_TYPE=PRODUCTION, crear la base de datos PostgreSQL
createdb contexto_fisica   # o crearla desde psql

# 5. Ejecutar migraciones
python manage.py makemigrations juego   # primera vez
python manage.py migrate

# 6. Cargar datos (en este orden — seed_vocabulario debe ir primero)
python manage.py seed_vocabulario   # carga el vocabulario completo (~18 264 palabras)
python manage.py seed_targets       # carga las ~300 palabras objetivo (FK a Vocabulario)
python manage.py seed_pistas        # limpia y reinserta las pistas (con validación anti-spoiler)

# 7. Generar al menos un juego jugable (ver sección "Agregar un juego nuevo")
python manage.py generar_juego energía

# 8. Crear superusuario (opcional, para el admin)
python manage.py createsuperuser

# 9. Iniciar servidor
python manage.py runserver
```

Abrí `http://localhost:8000` en el navegador.

## Agregar un juego nuevo

Un `Target` recién creado por `seed_targets` **no es jugable todavía** — existe en la BD pero
con `disponible=False`. Para habilitarlo hay que precalcular su ranking contra las 18.264
palabras del vocabulario:

```bash
python manage.py generar_juego <palabra>
```

Esto carga el embedding (`.npz`) **solo durante esta corrida** (nunca en el servidor web),
calcula la similitud coseno contra todo el vocabulario y guarda 18.264 filas en
`RankingPalabra`. Al terminar, `Target.disponible` pasa a `True` y la palabra puede salir como
target del día (`/api/target/actual`) o al pedir un juego nuevo desde el botón de dado.

- La palabra debe existir en `Vocabulario` (correr `seed_vocabulario` si no) y tener un `Target`
  asociado (correr `seed_targets`, o crearlo desde el admin).
- Si ya tiene un ranking generado, el comando aborta para no pisarlo por accidente:
  ```bash
  python manage.py generar_juego <palabra> --forzar   # borra y recalcula
  ```
- Otras opciones: `--batch-size N` (tamaño de batch del insert masivo, default 5000) y
  `--embedding-path RUTA` (por si se quiere usar un `.npz` distinto al de `settings.EMBEDDING_PATH`).
- El comando termina con un resumen (filas insertadas, rank de la propia palabra — debe ser 1 —,
  y tiempos de carga/cálculo/inserción).

## Admin

`http://localhost:8000/admin/` — permite editar targets, pistas y consultar el vocabulario.

## Estructura de datos

- `data/embedding_fisica.npz`: vocabulario (~18 k palabras) y embeddings preentrenados
- `data/vocabulario.csv`: vocabulario completo con índice (= fila en el embedding) y frecuencia
- `data/targets_contexto.csv`: ~300 palabras objetivo con rank y frecuencia
- `data/pistas.json`: pistas progresivas por palabra (de menos a más obvia)

## Notas

- `seed_pistas` limpia y reinserta `Pista` en cada corrida, así que editar un texto en
  `pistas.json` y volver a correr el comando sí actualiza el contenido en la base de datos.
- `seed_vocabulario` debe correr antes que `seed_targets`/`seed_pistas` la primera vez. Si se
  corre después de que ya existan `Target`, falla con `ProtectedError` (la FK protege contra
  borrados accidentales del vocabulario en uso).
