# eventos-django

[![backend](https://github.com/milionhub/eventos-django/actions/workflows/backend.yml/badge.svg)](https://github.com/milionhub/eventos-django/actions/workflows/backend.yml)
[![frontend](https://github.com/milionhub/eventos-django/actions/workflows/frontend.yml/badge.svg)](https://github.com/milionhub/eventos-django/actions/workflows/frontend.yml)

Plataforma de gestión de eventos y entradas digitales con QR: los organizadores crean eventos y categorías de entrada, los asistentes reservan desde el móvil y el personal valida los accesos escaneando con la cámara.

**Stack:** Angular · Django REST Framework · PostgreSQL · Docker

> 🚧 En desarrollo — Fases 1 a 5 completadas (auth, organizaciones, eventos, reservas, entradas con QR, validación en la puerta con la cámara del móvil, dashboard con estadísticas, gestión de asistentes con exportación CSV y app instalable). Consulta [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Destacado: reservas sin sobreventa

Cuando quedan pocas plazas, muchas personas pulsan «Reservar» a la vez. El código tiene que garantizar que **nunca se reservan más plazas de las que hay**, y eso se demuestra con tests contra PostgreSQL ([ADR-0004](docs/adr/0004-concurrencia-reservas-checkin.md)).

### El problema: «leer, comprobar y escribir»
```python
ticket_type = TicketType.objects.get(pk=id)        # leer: queda 1 plaza
if ticket_type.reserved_count < ticket_type.capacity:
    ticket_type.reserved_count += 1                # entre la lectura y la escritura
    ticket_type.save()                             # otras peticiones leyeron lo mismo
```
Con este código, el test de **50 personas a la vez para 10 plazas** confirma **las 50 reservas**. Ni siquiera la restricción `reserved_count <= capacity` de la base de datos lo impide: todas escriben el mismo valor bajo y las escrituras se pisan.

### La solución: un `UPDATE` condicional
```sql
UPDATE events_tickettype
   SET reserved_count = reserved_count + 1
 WHERE id = %s AND reserved_count < capacity
```
Comprobar e incrementar es **una sola sentencia**. PostgreSQL bloquea la fila durante el `UPDATE`: la siguiente petición espera, vuelve a evaluar el `WHERE` con el valor nuevo y, si ya no queda sitio, no actualiza nada (`SoldOut`). Todo va en una transacción: si después falla algo, la plaza vuelve sola. Ver [`ticketing/services.py`](backend/apps/ticketing/services.py).

Defensa en profundidad, en la base de datos:
- `CHECK (reserved_count <= capacity)`: última barrera aunque un bug se saltara el servicio.
- Índice único **parcial** `(user, event) WHERE status = 'CONFIRMED'`: una reserva por persona y evento. También cubre el **doble clic**: 5 clics simultáneos crean 1 reserva y el contador queda en 1.

### Un deadlock real que encontraron los tests
El test que lanza reservas mientras se cancela el evento fallaba en un tercio de las pasadas con `deadlock detected`:
1. Cancelar el evento bloqueaba la fila del **evento** (`FOR UPDATE`) y esperaba a la de la **categoría**.
2. Una reserva ya tenía la **categoría** bloqueada y, al insertar, PostgreSQL comprueba la clave foránea hacia el evento con un bloqueo `FOR KEY SHARE`… incompatible con `FOR UPDATE`.

La solución fue bloquear el evento con **`FOR NO KEY UPDATE`** (`select_for_update(no_key=True)`): sigue serializando los cambios del evento pero deja pasar las comprobaciones de clave foránea. Ahora pasa 20 de 20 veces.

### Los tests
```bash
cd backend && uv run pytest apps/ticketing/tests/test_concurrency.py -v
```
| Test | Qué garantiza |
|---|---|
| 50 personas, 10 plazas | Exactamente 10 confirmadas y 40 «agotado» |
| Doble clic | 1 reserva; las rechazadas devuelven su plaza |
| Cancelar la misma reserva 5 veces a la vez | La plaza se libera una sola vez (contador en 0, no en −4) |
| Reservas mientras se cancela el evento | Ninguna reserva confirmada sobrevive en un evento cancelado |
| Reservas y cancelaciones mezcladas | El contador coincide siempre con las reservas confirmadas |

Cada test se validó también **quitando la protección** que comprueba, para asegurar que de verdad detecta el fallo.

## Destacado: una entrada no entra dos veces

En la puerta puede haber varias personas escaneando a la vez, y alguien puede enseñar la misma entrada (o una captura) en dos accesos. La entrada pasa de `VALID` a `USED` con el mismo patrón que las reservas, un `UPDATE` condicional ([`checkin/services.py`](backend/apps/checkin/services.py)):

```sql
UPDATE ticketing_ticket
   SET status = 'USED', checked_in_at = now(), checked_in_by_id = %s
 WHERE id = %s AND status = 'VALID'
```
1 fila actualizada → **Válida**. 0 filas → otro escaneo ganó la carrera: **Ya utilizada**, con la hora a la que entró. Cada intento, aceptado o no, queda registrado en `CheckInLog` con quién y cuándo.

### La trampa: el `UPDATE` con una subconsulta
La primera versión filtraba entrada y evento en una sola línea de Django:
```python
Ticket.objects.filter(token=token, status="VALID", reservation__event=event).update(status="USED")
```
Parece lo mismo, pero el filtro a través de `reservation__event` obliga a Django a escribir `UPDATE … WHERE id IN (SELECT … WHERE status = 'VALID' AND …)`: **todas** las condiciones, incluida `status = 'VALID'`, acaban dentro de la subconsulta. Cuando el segundo escaneo espera al primero, PostgreSQL vuelve a comprobar la fila ya actualizada (*EvalPlanQual*), pero no vuelve a ejecutar la subconsulta: solo mira `id IN (…)`, que sigue cumpliéndose. Resultado: **los dos escaneos daban «Válida»**. El test de concurrencia lo reprodujo 10 de 10 veces.

La solución: primero se busca la entrada (y se comprueba que es de ese evento) y después se hace el `UPDATE` filtrando **solo por columnas de la propia fila** (`id` y `status`). Ahora pasa 20 de 20 veces.

### Los tests
```bash
cd backend && uv run pytest apps/checkin/tests/test_concurrency.py -v
```
| Test | Qué garantiza |
|---|---|
| Dos puertas escanean la misma entrada a la vez | 1 «Válida» + 1 «Ya utilizada» |
| 10 escaneos simultáneos de la misma entrada | 1 «Válida», 9 «Ya utilizada» y los 10 intentos registrados |

Los otros cinco resultados posibles (entrada no válida, de otro evento, cancelada, fuera de horario y sin permiso) tienen sus propios tests en `test_scan.py` y `test_api.py`. Para probarlo con un móvil de verdad, ver la [guía para el móvil](docs/guia-movil.md).

## Destacado: cifras que cuadran y un CSV que no se puede usar contra ti

### Estadísticas sin cifras infladas
El dashboard muestra, por evento, las plazas (suma de los cupos de las categorías), las reservas y los accesos. Lo natural en Django es anotarlo todo en la misma consulta:
```python
Event.objects.annotate(
    seats=Sum("ticket_types__capacity"),
    checked_in=Count("reservations__ticket", filter=Q(reservations__ticket__status="USED")),
)
```
Pero son **dos relaciones uno-a-muchos en el mismo `JOIN`**: cada cupo se suma una vez por cada entrada y cada entrada se cuenta una vez por cada categoría. Con 2 categorías (15 plazas) y 4 reservas, 3 de ellas dentro, salía **60 plazas, 16 reservas y 6 dentro** en vez de 15, 4 y 3. Ningún error, solo números falsos.

La solución es calcular cada cifra en su propia **subconsulta correlacionada** (`Subquery` + `OuterRef`, en [`checkin/selectors.py`](backend/apps/checkin/selectors.py)): cada una agrupa solo su relación, y el número de consultas no crece con el número de eventos (un test comprueba que son las mismas con 1 evento que con 5).

### Exportación CSV protegida frente a inyección de fórmulas
El CSV de asistentes lleva datos que escribe cualquiera al registrarse, y el organizador lo abre en Excel. Un nombre como `=HYPERLINK("https://example.com";"Clic")` se convertiría en un enlace (o en algo peor). Por eso toda celda que empieza por `= + - @`, tabulador o retorno de carro se escribe con un apóstrofo delante, que Excel interpreta como «esto es texto» ([`ticketing/exports.py`](backend/apps/ticketing/exports.py), recomendación de OWASP). Además:
- separador `;` y BOM UTF-8, para que Excel en español lo abra bien a la primera;
- las horas, en la zona horaria del organizador (`?tz=Europe/Madrid`);
- se genera **en streaming**, sin cargar a todos los asistentes en memoria, y con `Cache-Control: no-store`.

### App instalable, pero nunca con datos viejos
La web se puede instalar en el móvil como una app (PWA con `@angular/service-worker`). El service worker guarda **solo los archivos de la aplicación**: la API y las imágenes subidas van siempre a la red. Sin conexión, la app abre, pero no enseña aforos ni entradas que podrían estar desactualizados. Cómo instalarla, en la [guía para el móvil](docs/guia-movil.md#extra--instalar-la-app-en-el-móvil-pwa).

## Cómo ejecutarlo

### Requisitos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (para PostgreSQL)
- [uv](https://docs.astral.sh/uv/) (instala Python 3.13 automáticamente)
- [Node.js 24](https://nodejs.org/)

### Primera vez
```bash
cp .env.example .env               # valores de desarrollo; cambia DJANGO_SECRET_KEY
docker compose up -d db            # PostgreSQL 17

cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser   # opcional, para entrar en /admin/
uv run pre-commit install                 # ruff y prettier antes de cada commit

cd ../frontend
npm install
```

### Arrancar
En dos terminales:
```bash
cd backend && uv run python manage.py runserver   # API en http://127.0.0.1:8000/api/docs/
cd frontend && npm start                          # web en http://localhost:4200
```
Angular redirige `/api` a Django mediante un proxy, así que basta con abrir `http://localhost:4200`.

### Tests y calidad
| | Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|---|
| Tests | `uv run pytest` | `npm test` |
| Cobertura | `uv run pytest --cov` (mínimo 98 %; la CI falla por debajo) | — |
| Lint | `uv run ruff check .` | `npm run lint` |
| Formato | `uv run ruff format .` | `npm run format` |
| Vulnerabilidades | `uv export --frozen --no-emit-project > req.txt && uvx pip-audit -r req.txt --disable-pip` | `npm audit --audit-level=high` |

Los tests del backend usan PostgreSQL (nunca SQLite), así que el contenedor `db` debe estar arrancado.

La CI ejecuta las dos auditorías en cada cambio y, además, todos los lunes, para enterarse de las vulnerabilidades nuevas aunque no se toque el código.

### Cliente de la API
El cliente Angular se genera a partir del esquema OpenAPI de Django ([ADR-0007](docs/adr/0007-cliente-api-generado.md)). Tras cambiar la API:
```bash
cd frontend && npm run api:generate   # actualiza backend/schema.yml y src/app/core/api/
```
La CI falla si alguno de los dos queda desactualizado.

### Probar el escáner en un móvil
La cámara del móvil solo funciona con HTTPS, así que se expone el servidor de desarrollo con un túnel gratuito de [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/). Paso a paso en la [guía para el móvil](docs/guia-movil.md).

> ⚠️ Mientras el túnel está abierto, la aplicación (con `DEBUG` activado) es accesible desde internet. Ciérralo al terminar.

## Documentación
- [Requisitos y reglas de negocio](docs/requirements.md)
- [Modelo de datos](docs/data-model.md)
- [Arquitectura y API](docs/architecture.md)
- [Wireframes](docs/wireframes.md)
- [Identidad visual](docs/design.md)
- [Decisiones de arquitectura (ADR)](docs/adr/README.md)
- [Seguridad: revisión y riesgos aceptados](docs/security.md)
- [Guía: probar el escáner en un móvil](docs/guia-movil.md)
- [Guía: probar la Fase 5 (dashboard, asistentes, CSV y PWA)](docs/guia-pruebas-fase5.md)
