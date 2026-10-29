# ADR-0004 — Concurrencia: UPDATE condicional + restricciones de BD

**Estado:** Aceptado · **Fecha:** 2026-10-27

## Contexto
Dos puntos críticos:
1. **Reservas:** N usuarios compiten por las últimas plazas → riesgo de sobreventa.
2. **Check-in:** la misma entrada se escanea en dos puertas a la vez → riesgo de doble acceso.

El patrón ingenuo "leer → comprobar en Python → escribir" falla: entre la lectura y la escritura otra petición puede colarse.

## Decisión

### Reservas
- Contador `TicketType.reserved_count`.
- Incremento **atómico y condicional** en una sola sentencia SQL:
  `UPDATE ... SET reserved_count = reserved_count + 1 WHERE id = X AND reserved_count < capacity`.
  Si afecta a 0 filas → `SoldOut`.
- Todo dentro de `transaction.atomic()`: si después falla la creación de la reserva (p. ej. por el `UniqueConstraint` de una reserva duplicada), el contador vuelve atrás.
- Defensa en profundidad: `CheckConstraint(reserved_count <= capacity)` en PostgreSQL.

### Check-in
- `UPDATE ticket SET status='USED' ... WHERE token=X AND status='VALID' AND event=Y`.
  1 fila → `VALID`; 0 filas → se consulta el ticket para clasificar el rechazo.
- PostgreSQL bloquea la fila durante el UPDATE: el segundo escaneo concurrente espera, vuelve a evaluar el `WHERE` y ya no coincide.

### Tests
- `pytest.mark.django_db(transaction=True)` + `ThreadPoolExecutor` lanzando peticiones simultáneas **contra PostgreSQL** (SQLite no sirve para esto).
- Caso estrella: 50 reservas concurrentes sobre un cupo de 10 → exactamente 10 confirmadas.

## Consecuencias
- ✅ Sin bloqueos explícitos largos, y escala bien.
- ✅ La BD garantiza la invariante aunque haya un bug en Python.
- ⚠️ `reserved_count` está desnormalizado: hay que actualizarlo siempre a través del servicio (nunca con `.save()` directo). Un test de consistencia lo verifica.

## Nota de implementación (Fase 3)
- Las operaciones que bloquean un evento usan `select_for_update(no_key=True)` (`FOR NO KEY UPDATE`), no `FOR UPDATE`. Insertar una reserva comprueba su clave foránea al evento con un bloqueo `FOR KEY SHARE`, incompatible con `FOR UPDATE`: una reserva con la categoría bloqueada y una cancelación del evento esperando esa categoría producían un *deadlock*. Lo detectó el test de concurrencia de reservas frente a cancelación.
- `reserve()` vuelve a leer el estado del evento tras el `UPDATE` (ya con la fila de la categoría bloqueada) y `cancel_event()` bloquea las categorías antes de anular reservas: así ninguna reserva confirmada sobrevive a la cancelación del evento.

## Nota de implementación (Fase 4)
- El `UPDATE` del check-in filtra **solo por columnas de la propia entrada**: `WHERE id = X AND status = 'VALID'`. La comprobación de que la entrada es de ese evento se hace antes, al buscarla por `token`, y no dentro del `UPDATE` como sugería el esquema de arriba.
- Motivo: en Django, filtrar por `reservation__event` dentro del `.update()` genera `UPDATE … WHERE id IN (SELECT …)`, con `status = 'VALID'` dentro de la subconsulta. Cuando un escaneo concurrente espera al primero, PostgreSQL revalúa la fila actualizada (*EvalPlanQual*) pero no vuelve a ejecutar la subconsulta, así que los dos escaneos validaban. El test de concurrencia lo reprodujo 10 de 10 veces; con el filtro por columnas propias pasa 20 de 20.
- Regla general para este proyecto: **un `UPDATE` condicional que protege una invariante no debe depender de otras tablas.**

## Alternativas descartadas
- **`select_for_update()`:** también es válido, pero serializa más y el código es más largo. Lo mencionaremos en el README como alternativa.
- **Contar reservas con `COUNT(*)` en cada petición:** no es seguro sin bloqueo de tabla.
- **Bloqueo distribuido con Redis:** innecesario con una sola BD.
