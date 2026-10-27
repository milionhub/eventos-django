# CLAUDE.md — reglas del proyecto eventos-django

Plataforma de gestión de eventos y entradas QR. Proyecto de **portfolio y aprendizaje** (Django/DRF + Angular). Presupuesto **0 €**.

## Documentación de referencia (leer antes de implementar)
- `docs/ROADMAP.md` — fases y estado actual
- `docs/requirements.md` — reglas de negocio (RN-xx) y matriz de permisos
- `docs/data-model.md` — modelos, restricciones e índices
- `docs/architecture.md` — capas, endpoints y estructura de carpetas
- `docs/adr/` — decisiones técnicas cerradas

## Forma de trabajo
- El propietario del proyecto **supervisa y revisa**; Claude implementa en bloques pequeños.
- Al terminar cada bloque, Claude informa: archivos creados, modificados y borrados, decisiones tomadas y cosas pendientes de confirmar.
- Antes de cada bloque: objetivo concreto + criterios de aceptación.
- No hacer commits ni push sin que se pida.

## Reglas
- Respetar la arquitectura y los ADR. Para cambiar una decisión, proponer un ADR nuevo en vez de cambiarla en silencio.
- No añadir dependencias sin justificarlo. Nada de servicios de pago.
- No implementar funcionalidades fuera del alcance del MVP (ver `requirements.md` §6).
- No tocar módulos no relacionados con la tarea.
- **Toda regla de negocio va en `services.py`** y lleva test. Las vistas son finas.
- **Todos los permisos se comprueban en el backend.** Las restricciones visuales de Angular son solo UX.
- Acceso a recursos de otra organización → 404.
- Tests de concurrencia contra PostgreSQL, nunca SQLite.
- Explicar las decisiones técnicas importantes (el proyecto también es para aprender).

## Convenciones
- **Código, identificadores y comentarios en inglés.** Documentación (`docs/`, README) en español.
- Commits: Conventional Commits en español (`feat(ticketing): reserva atómica con control de cupo`).
- Backend: ruff (lint + formato), tipado en las firmas de servicios y selectores, tests en `apps/<app>/tests/`.
- Frontend: componentes standalone, signals, `@if`/`@for`, formularios reactivos tipados, features con carga diferida. No editar `core/api/` (es código generado).

## Comandos

Requisitos: Docker Desktop arrancado, `uv`, Node 24.

```bash
docker compose up -d db                      # PostgreSQL 17 (desde la raíz)

# backend/ (todo vía uv; Python 3.13 lo gestiona uv)
uv sync                                      # instalar dependencias
uv run python manage.py migrate
uv run python manage.py runserver            # http://127.0.0.1:8000/api/docs/
uv run python manage.py createsuperuser      # para entrar en /admin/
uv run pytest                                # tests (usan PostgreSQL)
uv run ruff check . && uv run ruff format .  # lint + formato

# frontend/ (Angular 22, tests con Vitest)
npm install
npm start                                    # http://localhost:4200 (proxy /api → :8000)
npm test                                     # tests una vez (npm run test:watch en modo watch)
npm run lint
npm run format                               # prettier
npm run build
```

Nota: en `DATABASE_URL` usar `127.0.0.1`, no `localhost` (en Windows, `::1` se cuelga).
