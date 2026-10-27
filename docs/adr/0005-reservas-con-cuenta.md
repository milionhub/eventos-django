# ADR-0005 — Reservas solo con cuenta, 1 entrada por reserva

**Estado:** Aceptado · **Fecha:** 2026-10-27

## Contexto
Las reservas como invitado exigen enviar la entrada por email (servicio externo) o enlaces mágicos, y complican la deduplicación.

## Decisión
- Para reservar hay que estar autenticado.
- Una reserva genera exactamente una entrada.
- Máximo una reserva `CONFIRMED` por usuario y evento, mediante un índice único parcial. Esto también cubre el doble clic: la segunda petición recibe `409 already_reserved`.

## Consecuencias
- ✅ "Mis entradas" es trivial y no hace falta ningún servicio de email.
- ✅ La deduplicación la garantiza la BD, sin claves de idempotencia.
- ⚠️ Un usuario no puede comprar entradas para otras personas (aceptable en el MVP).

## Futuro
Reservas como invitado y N entradas por reserva → `Ticket.reservation` pasa de OneToOne a FK.
