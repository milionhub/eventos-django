# Arquitectura

> Estado: **borrador Fase 0**.

## Visión general

```
 Navegador (escritorio / móvil, PWA)
        │
        ▼
 Angular SPA ──── /api/* ───►  Django + DRF  ───►  PostgreSQL
 (dev: ng serve + proxy)       (monolito modular)
```

- En desarrollo, Angular hace de proxy de `/api` hacia Django (`proxy.conf.json`). El navegador ve **un solo origen**: no hace falta CORS y la cookie de refresh funciona sin configuración especial.
- En `docker compose` (modo demo), **nginx** sirve el build de Angular y hace de proxy de `/api` a Django (gunicorn). Es el mismo modelo de un solo origen.

## Backend

### Herramientas
| Uso | Herramienta |
|---|---|
| Dependencias y entorno | **uv** (`pyproject.toml` + `uv.lock`) |
| API | Django REST Framework |
| Auth | `djangorestframework-simplejwt` (+ app de blacklist) |
| OpenAPI | `drf-spectacular` |
| QR | `segno` (Python puro, genera SVG sin depender de Pillow) |
| Tests | pytest + pytest-django + factory-boy |
| Lint y formato | ruff |
| Configuración | `django-environ` (lee `.env`) |

### Estructura

```text
backend/
├── pyproject.toml
├── manage.py
├── config/
│   ├── settings/  (base.py, dev.py, test.py, prod.py)
│   ├── urls.py
│   └── wsgi.py / asgi.py
├── apps/
│   ├── core/           # TimeStampedModel, permisos base, excepciones, healthcheck, seed_demo
│   ├── accounts/       # User, registro, auth, /me
│   ├── organizations/  # Organization, Membership
│   ├── events/         # Event, TicketType, EventStaff, endpoints públicos
│   ├── ticketing/      # Reservation, Ticket, QR
│   └── checkin/        # CheckInLog, validación, stats de accesos
└── tests/              # o tests/ dentro de cada app (ver la convención en CLAUDE.md)
```

### Capas dentro de cada app

| Fichero | Responsabilidad |
|---|---|
| `models.py` | Datos y restricciones de BD. Sin lógica de negocio compleja. |
| `services.py` | **Escrituras con reglas de negocio** (reservar, cancelar, publicar, validar). Funciones explícitas, transaccionales y testeables sin HTTP. |
| `selectors.py` | **Lecturas** reutilizables y filtradas por permisos (p. ej. `events_for_user(user)`). |
| `serializers.py` | Validación de entrada y forma de salida. **No** llaman a `.save()` con lógica de negocio. |
| `views.py` | Fina: autentica → llama a selector o servicio → serializa. |
| `permissions.py` | Clases de permiso de DRF. |

Las excepciones de dominio (`SoldOut`, `AlreadyReserved`, `CancellationWindowClosed`…) heredan de `DomainError` y un *exception handler* global las convierte en respuestas HTTP coherentes.

### Aislamiento multi-organización
- Las vistas de organización usan un mixin `OrganizationScopedMixin` que resuelve la organización a partir del `slug` de la URL, comprueba la membresía y el rol, y **filtra `get_queryset()`**. Así es imposible olvidarse del filtro en un endpoint.
- Si no hay membresía → `404`.
- Tests: una matriz parametrizada de rol × organización ajena × endpoint.

### Formato de errores
```json
{ "code": "sold_out", "detail": "No quedan plazas en esta categoría." }
```
Los errores de validación de DRF mantienen su formato estándar por campo.

## API (v1)

Prefijo `/api/v1/`. Paginación por página (`?page=`, tamaño 20). Solo JSON: el único cliente es la SPA, así que no se aceptan formularios (`DEFAULT_PARSER_CLASSES`).

### Auth y cuenta
| Método | Ruta | Descripción |
|---|---|---|
| POST | `auth/register/` | Crea la cuenta |
| POST | `auth/login/` | Devuelve `access`; deja el `refresh` en una cookie httpOnly |
| POST | `auth/refresh/` | Lee la cookie y devuelve un `access` nuevo (rotación) |
| POST | `auth/logout/` | Invalida el refresh (blacklist) y borra la cookie |
| GET | `auth/me/` | Usuario + membresías |

### Público
| Método | Ruta |
|---|---|
| GET | `public/events/` (publicados y no finalizados; filtros `?q=`, `?from=`) |
| GET | `public/events/{slug}/` (incluye categorías con plazas disponibles) |

### Asistente
| Método | Ruta | Descripción |
|---|---|---|
| POST | `reservations/` | `{ "ticket_type": id }` → reserva + entrada |
| POST | `reservations/{uuid}/cancel/` | |
| GET | `me/tickets/` | Mis entradas |
| GET | `me/tickets/{uuid}/` | Detalle (incluye el token) |
| GET | `me/tickets/{uuid}/qr.svg` | QR en SVG |

### Organizador (`organizations/{org_slug}/…`)
| Método | Ruta |
|---|---|
| GET, POST | `organizations/` (mis organizaciones / crear) |
| GET, PATCH | `organizations/{org}/` |
| GET, POST, PATCH, DELETE | `organizations/{org}/members/[{id}/]` |
| GET, POST | `organizations/{org}/events/` |
| GET, PATCH | `organizations/{org}/events/{id}/` |
| POST | `…/events/{id}/publish/`, `…/events/{id}/cancel/` |
| GET, POST, PATCH, DELETE | `…/events/{id}/ticket-types/[{id}/]` |
| GET, POST, DELETE | `…/events/{id}/staff/[{id}/]` |
| GET | `…/events/{id}/reservations/` (asistentes; `?q=` por nombre o email, `?status=` del estado de la entrada) |
| POST | `…/events/{id}/reservations/{uuid}/cancel/` |
| GET | `…/events/{id}/attendees.csv` (mismos filtros que el listado + `?tz=Europe/Madrid`; separador `;` y BOM UTF-8 para Excel; celdas que empiezan por `= + - @` escapadas) |
| GET | `…/events/{id}/stats/` |
| GET | `organizations/{org}/stats/` |

### Check-in
| Método | Ruta | Descripción |
|---|---|---|
| GET | `checkin/events/` | Eventos en los que puedo validar |
| POST | `checkin/events/{id}/scan/` | `{ "token": "..." }` → `{ "result": "VALID", "ticket": {...} }` |
| GET | `checkin/events/{id}/logs/` | Últimos intentos |

Documentación en vivo: `/api/docs/` (Swagger) y `/api/schema/`.

## Frontend

### Herramientas
| Uso | Herramienta |
|---|---|
| Framework | Angular (última versión estable) con **componentes standalone, signals y la nueva sintaxis de control de flujo** |
| UI | Angular Material |
| Cliente API | **Generado a partir del OpenAPI** (`ng-openapi-gen`) → tipos desde Django hasta Angular |
| QR (escáner) | `@zxing/ngx-scanner` |
| PWA | `@angular/service-worker` configurado a mano (`ngsw-config.json`): solo guarda en caché los archivos de la app y Google Fonts; **nunca la API ni `/media`**. Activo solo en el build de producción |
| Tests unitarios | El runner por defecto del CLI de Angular |
| E2E | Playwright |
| Lint y formato | angular-eslint + Prettier |

### Estructura

```text
frontend/src/app/
├── core/
│   ├── api/            # código generado (no se edita a mano)
│   ├── auth/           # AuthService (signals), interceptor JWT con refresh, guards
│   └── layout/         # shell, navbar, menú responsive
├── shared/             # componentes, pipes y utilidades reutilizables
└── features/           # cada una con carga diferida (lazy)
    ├── public-events/  # listado y detalle público
    ├── auth/           # login, registro
    ├── my-tickets/     # mis entradas, entrada con QR
    ├── organizer/      # organizaciones, eventos, categorías, staff, asistentes, dashboard
    └── checkin/        # selección de evento + escáner
```

### Estado y datos
- Sin NgRx: **servicios con signals** por feature. Es suficiente para este tamaño.
- El `access token` se guarda en memoria (una signal). El `refresh` vive en una cookie httpOnly, invisible para JS.
- Un interceptor añade el `Authorization` y, ante un 401, intenta un refresh una vez; si falla, cierra la sesión.
- Guards funcionales: `authGuard`, `orgRoleGuard(roles)`.

## Entorno de desarrollo

- **PostgreSQL en Docker** (`compose.yaml`, servicio `db`).
- Django y Angular **en local** (más rápido en Windows: recarga en caliente sin problemas de volúmenes).
- `compose.yaml` completo (db + backend + frontend con nginx) para el **modo demo**: `docker compose --profile demo up`.
- Probar la cámara en el móvil: túnel HTTPS gratuito con `cloudflared tunnel --url http://localhost:4200`.

## CI (GitHub Actions)

- **backend**: `uv sync` → `ruff check` + `ruff format --check` → `pytest` contra un *service container* de PostgreSQL → comprobar que el esquema OpenAPI no tiene cambios sin commitear.
- **frontend**: `npm ci` → lint → tests → `ng build`.
- **e2e** (desde la Fase 6): compose + Playwright.
