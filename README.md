# eventos-django

[![backend](https://github.com/milionhub/eventos-django/actions/workflows/backend.yml/badge.svg)](https://github.com/milionhub/eventos-django/actions/workflows/backend.yml)
[![frontend](https://github.com/milionhub/eventos-django/actions/workflows/frontend.yml/badge.svg)](https://github.com/milionhub/eventos-django/actions/workflows/frontend.yml)

Plataforma de gestión de eventos y entradas digitales con QR: los organizadores crean eventos y categorías de entrada, los asistentes reservan desde el móvil y el personal valida los accesos escaneando con la cámara.

**Stack:** Angular · Django REST Framework · PostgreSQL · Docker

> 🚧 En desarrollo — Fases 1 a 3 completadas (auth, organizaciones, eventos, reservas y entradas con QR). Consulta [`docs/ROADMAP.md`](docs/ROADMAP.md).

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
| Lint | `uv run ruff check .` | `npm run lint` |
| Formato | `uv run ruff format .` | `npm run format` |

Los tests del backend usan PostgreSQL (nunca SQLite), así que el contenedor `db` debe estar arrancado.

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
- [Guía: probar el escáner en un móvil](docs/guia-movil.md)
