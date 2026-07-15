# Módulo de Mantenimiento - ERP

Módulo de mantenimiento preventivo/correctivo de flotilla, hecho en
**Python + FastAPI + SQLAlchemy**.

## Qué hace

- Da de alta unidades (económicos), marcando cada una como **propia** (de
  la flotilla, se puede actualizar via Samsara) o **pública** (vehículo de
  cliente externo, todo manual — para cuando trabajan al público).
- Define una regla de servicio por unidad (cada cuántos km toca preventivo).
- Registra mantenimientos con tipo **preventivo**, **correctivo**, o
  **otra reparación** (para trabajos manuales que no encajan en los
  anteriores — típico en unidades públicas), con subtipo (eléctrico,
  mecánico, soldadura), fecha de entrada/salida y costo.
- Calcula automáticamente el estado de cada unidad:
  - **al_corriente**: falta más de 500 km para el próximo servicio.
  - **proximo**: quedan 500 km o menos.
  - **vencido**: ya se pasó del kilometraje del próximo servicio.
  - **sin_regla**: la unidad no tiene regla de servicio configurada.
- **Módulo de control de llantas**: por cada llanta se registra posición
  (delantera/trasera, izq/der), marca, modelo, número de serie (DOT), km
  de vida útil esperada y profundidad de dibujo. Cada inspección queda en
  un historial, y el estado de la llanta se marca igual
  (al_corriente/proximo/vencido) tomando el peor caso entre kilometraje
  recorrido y profundidad medida. Se puede dar de baja una llanta cuando
  se cambia (queda en el histórico).

El kilometraje se captura a mano por ahora (ver nota abajo sobre Samsara).

- **Contador de renovaciones**: cada llanta muestra cuántas llantas anteriores
  hubo en esa misma posición de esa unidad (útil para saber "cuántos
  renovados lleva" esa posición).
- **Alertas activas**: una sección al inicio del dashboard junta todas las
  unidades y llantas en estado "próximo" o "vencido", para no tener que
  revisar tabla por tabla.

## Control de accesos (usuarios y permisos por módulo)

Al entrar por primera vez, el sistema crea un usuario administrador por
defecto:

```
usuario: admin
contraseña: admin123
```

**Cambien esa contraseña de inmediato** desde `POST /api/auth/cambiar-password`
(o agreguen un botón en el dashboard si lo necesitan más adelante).

- El **admin** ve y edita todos los módulos, y puede crear más usuarios
  desde la sección "Administración de usuarios" del dashboard (solo visible
  para admins).
- Los **usuarios limitados** solo ven y pueden usar los módulos que se les
  asignen (Unidades, Mantenimientos, Llantas, Importar CSV) — el resto de
  secciones se ocultan automáticamente en su dashboard, y la API rechaza
  (403) cualquier intento de acceso a un módulo sin permiso.
- La sesión se guarda en una cookie firmada (7 días de duración). No hay
  base de datos de sesiones ni servicios externos involucrados.

**Importante para producción (Render):** definan la variable de entorno
`SECRET_KEY` con un valor propio y secreto (usada para firmar las cookies
de sesión). Si no se define, se usa una clave de desarrollo que no es
segura para producción.

## Correr en local (Mac Intel 2020)

```bash
cd mantenimiento-erp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abre http://localhost:8000 — ahí está el dashboard.
La base de datos es un archivo SQLite (`mantenimiento.db`) que se crea solo.

## Endpoints principales (API)

- `POST /api/unidades/` — crear unidad (con regla de servicio opcional)
- `GET /api/unidades/` — listar unidades con su estado calculado
- `PATCH /api/unidades/{id}/km` — actualizar kilometraje actual
- `POST /api/mantenimientos/` — registrar un mantenimiento
- `GET /api/mantenimientos/?unidad_id=1` — historial de una unidad

FastAPI genera documentación interactiva automática en `/docs`.

## Desplegar en Render

1. Sube este proyecto a un repo de GitHub.
2. En Render: **New > Web Service**, conecta el repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. (Opcional) Si luego quieren PostgreSQL en vez de SQLite, agrega la
   variable de entorno `DATABASE_URL` con la cadena de conexión de Render
   y agrega `psycopg2-binary` a `requirements.txt`. No hay que tocar
   nada más del código.

## Importar kilometraje desde Samsara (sin token, sin API)

En vez de conectar directo a la API de Samsara, el flujo es más simple:

1. En Samsara, entra al informe personalizado **"MANTENIMIENTO"** (o el que
   tenga la columna de odómetro), ejecútalo y descárgalo como **CSV**.
2. En el dashboard del módulo (http://localhost:8000), en la sección
   **"Importar kilometraje desde Samsara"**, sube ese CSV.
3. El sistema busca cada unidad por su nombre de Samsara (columna "Nombre"
   del CSV) y actualiza su `km_actual` automáticamente.

**Importante — mapeo de nombres:** si el nombre que usa Samsara (ej.
`AVEO 012`) es distinto al económico interno que usan en la flotilla,
captura ese nombre en el campo **"Nombre en Samsara"** al dar de alta la
unidad. Si son iguales, no hace falta llenarlo.

También hay un endpoint directo: `POST /api/importar/samsara-csv` (form-data,
campo `archivo`), por si luego se quiere automatizar la subida del archivo.

## Pendiente / siguiente paso (API directa de Samsara)

Si más adelante Jorgais da acceso a un token de API de Samsara, se puede
agregar un job que jale el odómetro directo (sin pasos manuales de
exportar/importar CSV) y llame internamente a la misma lógica que ya
existe — no habría que rediseñar nada de lo construido.
