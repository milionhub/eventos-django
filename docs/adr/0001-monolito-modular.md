# ADR-0001 — Monolito modular Django + SPA Angular

**Estado:** Aceptado · **Fecha:** 2026-10-27

## Contexto
Proyecto de portfolio con un solo desarrollador, presupuesto 0 € y el objetivo de aprender Django/DRF y Angular.

## Decisión
- Un único proyecto Django dividido en apps por dominio (`accounts`, `organizations`, `events`, `ticketing`, `checkin`) y una SPA Angular que consume la API REST.
- La lógica de negocio vive en `services.py` y `selectors.py`, no en vistas ni serializers.
- No se añaden Redis, Celery ni WebSockets hasta que haya una necesidad real.

## Consecuencias
- ✅ Un solo despliegue, una sola BD y transacciones ACID entre módulos (clave para reservas y check-in).
- ✅ Los límites entre apps hacen posible extraer un servicio en el futuro.
- ⚠️ Hay que vigilar los imports entre apps: `ticketing` puede depender de `events`, pero no al revés.

## Alternativas descartadas
- **Microservicios:** complejidad operativa sin ningún beneficio a esta escala.
- **Plantillas Django (sin SPA):** no cumple el objetivo de aprender Angular.
