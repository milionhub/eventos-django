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

## Alternativas descartadas
- **`select_for_update()`:** también es válido, pero serializa más y el código es más largo. Lo mencionaremos en el README como alternativa.
- **Contar reservas con `COUNT(*)` en cada petición:** no es seguro sin bloqueo de tabla.
- **Bloqueo distribuido con Redis:** innecesario con una sola BD.
