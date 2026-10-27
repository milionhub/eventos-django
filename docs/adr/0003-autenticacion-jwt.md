# ADR-0003 — JWT con refresh en cookie httpOnly

**Estado:** Aceptado · **Fecha:** 2026-10-27

## Contexto
SPA Angular + API DRF. JWT aparece con frecuencia en las ofertas de empleo, pero guardar tokens en `localStorage` los expone a XSS.

## Decisión
- `djangorestframework-simplejwt` con rotación de refresh y blacklist.
- **Access token** (15 min): se devuelve en el body y Angular lo guarda **solo en memoria**.
- **Refresh token** (7 días): en una cookie `httpOnly`, `SameSite=Strict`, `Secure` en producción, `path=/api/v1/auth/`.
- Vistas propias de login, refresh y logout que leen y escriben la cookie (simplejwt espera el refresh en el body).
- Mismo origen gracias al proxy (ver `architecture.md`), así que la cookie `Strict` funciona sin CORS.

## Consecuencias
- ✅ Un XSS no puede robar el refresh token.
- ✅ Al recargar la página, Angular llama a `auth/refresh/` y recupera la sesión.
- ⚠️ `SameSite=Strict` + POST solo en el endpoint de refresh mitiga el CSRF en ese endpoint; el resto de la API usa `Authorization: Bearer` y no es vulnerable a CSRF.
- ⚠️ Un poco más de código que el flujo estándar de simplejwt. Buen tema para la entrevista.

## Alternativas descartadas
- **Sesiones de Django + CSRF:** igual de seguras y más simples, pero menos alineadas con lo que piden las ofertas.
- **JWT en localStorage:** vulnerable a XSS.
