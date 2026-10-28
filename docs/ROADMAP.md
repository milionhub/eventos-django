# ROADMAP — eventos-django

**Proyecto:** plataforma de gestión de eventos y entradas digitales con QR
**Stack:** Angular + Django REST Framework + PostgreSQL
**Presupuesto:** 0 €
**Herramientas:** VS Code + Claude Code
**Estado:** Fase 0 — pendiente de revisión

> Detalle funcional: `requirements.md` · Datos: `data-model.md` · Técnica: `architecture.md` · Decisiones: `adr/`

---

## Cambios respecto a la v1 del roadmap

- Estimación revisada: **86–126 h** (antes 76–120), porque se aprenden dos frameworks a la vez y los tests se reparten por fases.
- **CI desde la Fase 1** y **tests en cada fase**. La Fase 6 pasa a ser solo de endurecimiento.
- El despliegue público deja de ser un objetivo. El entregable es repositorio + README + vídeo + `docker compose` (ADR-0006).
- OpenAPI y el cliente generado desde la Fase 1 (ADR-0007).
- Panel del administrador de plataforma = Django Admin.
- Dashboard recortado a lo esencial.
- `AGENTS.md` → `CLAUDE.md` (no se usa Cursor).
- Google Wallet baja de prioridad.

---

## Objetivos

1. Aprender Django y DRF en profundidad.
2. Aprender Angular moderno y TypeScript en un proyecto real.
3. Aplicar arquitectura modular, capa de servicios y buenas prácticas.
4. Resolver lógica de negocio, seguridad y **concurrencia** de forma demostrable.
5. App responsive + PWA usable desde el móvil.
6. Proyecto presentable en GitHub, LinkedIn y entrevistas.

---

## FASE 0 — Definición y arquitectura · 4–6 h

- [x] Recorridos de usuario → `requirements.md` §2
- [x] Reglas de reserva, cancelación y check-in → `requirements.md` §3
- [x] Roles y matriz de permisos → `requirements.md` §1 y §4
- [x] Modelo de datos con restricciones e índices → `data-model.md`
- [x] Arquitectura backend, frontend y API → `architecture.md`
- [x] Wireframes → `wireframes.md`
- [x] Decisiones técnicas → `adr/0001`–`0007`
- [x] Reglas para la IA → `CLAUDE.md`
- [x] **Revisión y validación por el propietario**

**Cierre:** documentos revisados y aprobados.

---

## FASE 1 — Cimientos · 10–15 h

**Repositorio y tooling**
- [x] `git init`, `.gitignore`, `.editorconfig`, `.env.example`
- [x] `compose.yaml` con PostgreSQL (el perfil `demo` se añade en la Fase 7)
- [x] pre-commit (ruff, prettier)

**Backend**
- [x] Proyecto Django con uv, settings divididos (base/dev/test/prod)
- [x] `accounts.User` propio **antes de la primera migración** (ADR-0002)
- [x] DRF + drf-spectacular + `/api/docs/`
- [x] App `core`: `TimeStampedModel`, `DomainError` + exception handler, `/api/v1/health/`
- [x] Apps vacías: organizations, events, ticketing, checkin
- [x] pytest + factory-boy + primer test

**Frontend**
- [x] Proyecto Angular (standalone, routing, SCSS) + Angular Material
- [x] Proxy `/api` → Django
- [x] Layout responsive (shell + navbar)
- [x] Generación del cliente API (`npm run api:generate`) + llamada a health
- [x] ESLint + Prettier + primer test

**CI**
- [x] GitHub Actions: backend (ruff + pytest con PostgreSQL) y frontend (lint + test + build)

**Cierre:** `docker compose up db` + backend + frontend en local; Angular muestra el estado de `/health/`; CI en verde.

---

## FASE 2 — Auth, organizaciones y eventos · 16–24 h

**Backend**
- [x] Registro, login, refresh y logout con cookie httpOnly; `/auth/me/` (ADR-0003)
- [x] Organization + Membership + servicios (crear organización → OWNER, gestión de miembros, RN-04)
- [x] `OrganizationScopedMixin` + permisos por rol
- [x] Event + TicketType + EventStaff con sus restricciones
- [x] Servicios: crear, editar, publicar (RN-09) y cancelar eventos; categorías (RN-13/14/15); staff
- [x] Endpoints públicos de eventos
- [x] Throttling de login
- [x] **Tests:** auth, matriz de permisos y aislamiento entre organizaciones, transiciones de estado

**Frontend**
- [x] AuthService con signals + interceptor con refresh + guards
- [x] Login y registro
- [x] Mis organizaciones / crear organización / miembros
- [x] Listado y formulario de eventos, pestañas Datos / Entradas / Staff
- [x] Listado y detalle público

**Cierre:** un organizador crea una organización, un evento y sus categorías, y lo publica; aparece en público. Otra organización recibe 404.

**Bloques de trabajo** (un commit por bloque):

| # | Bloque | Estado |
|---|---|---|
| 0 | Identidad visual `#4events` → [`design.md`](design.md) | ✅ |
| 1 | Auth backend: registro, login, refresh, logout, `me`, throttling | ✅ |
| 2 | Auth frontend: AuthService, interceptor, guard, login y registro | ✅ |
| 3 | Organizaciones backend: modelos, servicios, `OrganizationScopedMixin`, permisos | ✅ |
| 4 | Organizaciones frontend: mis organizaciones, crear, miembros | ✅ |
| 5 | Eventos backend: modelo, servicios y transiciones de estado | ✅ |
| 6 | Categorías y staff backend + endpoints públicos | ✅ |
| 7 | Eventos frontend (organizador): listado, formulario con pestañas, publicar/cancelar | ✅ |
| 8 | Público frontend (listado y detalle) + cierre de fase | ✅ |

---

## FASE 3 — Reservas y entradas · 14–20 h

- [x] Reservation + Ticket (UUID, token, índice único parcial)
- [x] Servicio `reserve()` con UPDATE condicional (ADR-0004)
- [x] Servicio `cancel_reservation()` (RN-20 a RN-24) y cascada al cancelar un evento (RN-10)
- [x] Endpoints del asistente + QR SVG (segno)
- [x] **Test de concurrencia:** 50 reservas sobre un cupo de 10 → 10 confirmadas
- [x] Test de consistencia de `reserved_count`
- [x] UI: botón de reserva en el detalle, Mis entradas, pantalla de entrada con QR
- [x] Throttling de reservas

**Cierre:** un asistente reserva desde el móvil y ve su QR; nunca se supera el cupo.

**Bloques de trabajo** (un commit por bloque):

| # | Bloque | Estado |
|---|---|---|
| 1 | Reserva atómica (backend): `Reservation` + `Ticket`, `reserve()` con UPDATE condicional, test 50 → 10 | ✅ |
| 2 | Cancelaciones (backend): asistente y organizador, cascada al cancelar evento (RN-10), RN-15 histórico | ✅ |
| 3 | Mis entradas y QR (backend): `me/tickets/`, detalle con token, `qr.svg` con segno | ✅ |
| 4 | Reservar y Mis entradas (frontend): botón de reserva, listado, entrada con QR | ✅ |
| 5 | Cierre: recorrido en móvil, ROADMAP y README (concurrencia) | ✅ |

---

## FASE 4 — Check-in · 12–18 h

- [ ] CheckInLog + servicio `scan()` con los 7 resultados (RN-32)
- [ ] Ventana de acceso (RN-29) y permisos (RN-28)
- [ ] **Test de concurrencia:** 2 escaneos simultáneos → 1 VALID + 1 ALREADY_USED
- [ ] UI: selector de eventos + escáner (`@zxing/ngx-scanner`) + resultado a pantalla completa con vibración
- [ ] Prueba en un móvil real mediante un túnel HTTPS (cloudflared)

**Cierre:** una entrada se valida desde el móvil y no se puede usar dos veces.

---

## FASE 5 — Dashboard, asistentes y móvil · 12–16 h

- [ ] Stats por evento (ocupación por categoría, accesos) y por organización
- [ ] Listado de asistentes con búsqueda y filtro + cancelación por el organizador
- [ ] Exportación CSV
- [ ] Repaso responsive completo (360 px), PWA instalable
- [ ] Recorridos completos probados en iPhone y Android

**Cierre:** los 5 recorridos (`requirements.md` §2) funcionan en escritorio y en móvil.

---

## FASE 6 — Endurecimiento · 10–15 h

- [ ] E2E con Playwright del recorrido completo (en CI)
- [ ] Revisión de seguridad (permisos, IDs enumerables, throttling, cabeceras, `DEBUG`, secretos)
- [ ] Revisión de cobertura de los servicios críticos
- [ ] Auditoría de dependencias (`pip-audit`, `npm audit`)
- [ ] Accesibilidad básica (contraste, etiquetas, foco)

**Cierre:** CI en verde con E2E, sin vulnerabilidades críticas conocidas.

---

## FASE 7 — Portfolio · 8–12 h

- [ ] `seed_demo`: organizaciones, eventos y usuarios de prueba por rol
- [ ] `docker compose --profile demo up` (nginx + gunicorn + db) funcionando a la primera
- [ ] README: qué es, GIF, arquitectura (diagrama), decisiones destacadas (concurrencia, auth, multi-organización), cómo ejecutarlo, credenciales demo, badge de CI
- [ ] Vídeo corto de demostración (móvil + escritorio)
- [ ] (Opcional) despliegue gratuito si es viable
- [ ] Publicación en LinkedIn + CV

**Cierre:** cualquiera puede entender el proyecto en 2 minutos y ejecutarlo con un comando.

---

## Estimación

| Fase | Horas |
|---|---:|
| 0 — Definición | 4–6 |
| 1 — Cimientos | 10–15 |
| 2 — Auth, organizaciones y eventos | 16–24 |
| 3 — Reservas | 14–20 |
| 4 — Check-in | 12–18 |
| 5 — Dashboard y móvil | 12–16 |
| 6 — Endurecimiento | 10–15 |
| 7 — Portfolio | 8–12 |
| **Total** | **86–126 h** |

Incluye aprendizaje y depuración. Si una fase se alarga mucho más, es señal de recortar alcance, no de seguir añadiendo horas.

---

## Después del MVP

**Alta:** emails de confirmación (backend de consola o plan gratuito), mejoras de accesibilidad.
**Media:** Stripe en modo test, dashboard en tiempo real, reservas como invitado, N entradas por reserva.
**Baja:** listas de espera, asientos numerados, transferencia de entradas, validación offline, Google Wallet.
**Requieren presupuesto:** Apple Wallet, dominio propio, infraestructura de pago.

---

## Estado actual

**Fase activa:** 4 — Check-in (Fase 3 cerrada el 2026-10-28: reserva desde el móvil con QR y cupo garantizado bajo concurrencia).
**Siguiente paso:** dividir la Fase 4 en bloques, empezando por `CheckInLog` y el servicio `scan()` con UPDATE condicional (ADR-0004, RN-28 a RN-32).
