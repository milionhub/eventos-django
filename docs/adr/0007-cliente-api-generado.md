# ADR-0007 — Cliente Angular generado a partir de OpenAPI

**Estado:** Aceptado · **Fecha:** 2026-10-27

## Contexto
Mantener a mano interfaces TypeScript que reflejen los serializers de DRF provoca desajustes silenciosos.

## Decisión
- `drf-spectacular` genera `schema.yml`, que se versiona en el repo.
- `ng-openapi-gen` genera servicios y modelos en `frontend/src/app/core/api/` (no se editan a mano).
- La CI falla si el esquema cambia y no se ha regenerado el cliente.

## Consecuencias
- ✅ Tipado de extremo a extremo: si cambia un serializer, Angular no compila hasta adaptarse.
- ✅ Obliga a documentar bien la API (`@extend_schema`).
- ⚠️ Un paso extra (`npm run api:generate`) cada vez que cambia la API.
