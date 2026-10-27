# ADR-0002 — Modelo de usuario propio con login por email

**Estado:** Aceptado · **Fecha:** 2026-10-27

## Contexto
Django recomienda definir un `AUTH_USER_MODEL` propio **antes de la primera migración**: cambiarlo después obliga a migraciones manuales muy delicadas.

## Decisión
`accounts.User` hereda de `AbstractUser`, elimina `username`, usa `email` (único, en minúsculas) como `USERNAME_FIELD` y tiene un `UserManager` propio.

## Consecuencias
- ✅ Login por email, que es lo que espera el usuario.
- ✅ Libertad para añadir campos en el futuro sin migraciones dolorosas.
- ⚠️ Hay que adaptar `UserAdmin` y los formularios del admin.

## Alternativas descartadas
- **User por defecto + perfil 1:1:** sigue exigiendo `username` y añade una consulta extra.
