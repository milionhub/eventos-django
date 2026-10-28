# eventos-django

[![backend](https://github.com/milionhub/eventos-django/actions/workflows/backend.yml/badge.svg)](https://github.com/milionhub/eventos-django/actions/workflows/backend.yml)
[![frontend](https://github.com/milionhub/eventos-django/actions/workflows/frontend.yml/badge.svg)](https://github.com/milionhub/eventos-django/actions/workflows/frontend.yml)

Plataforma de gestión de eventos y entradas digitales con QR: los organizadores crean eventos y categorías de entrada, los asistentes reservan desde el móvil y el personal valida los accesos escaneando con la cámara.

**Stack:** Angular · Django REST Framework · PostgreSQL · Docker

> 🚧 En desarrollo — Fases 1 y 2 completadas (auth, organizaciones y eventos). Consulta [`docs/ROADMAP.md`](docs/ROADMAP.md).

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

## Documentación
- [Requisitos y reglas de negocio](docs/requirements.md)
- [Modelo de datos](docs/data-model.md)
- [Arquitectura y API](docs/architecture.md)
- [Wireframes](docs/wireframes.md)
- [Identidad visual](docs/design.md)
- [Decisiones de arquitectura (ADR)](docs/adr/README.md)
