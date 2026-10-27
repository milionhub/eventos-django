# Requisitos del MVP

> Estado: **borrador Fase 0** — pendiente de validación del propietario del proyecto.
> Las decisiones marcadas con 🔒 están cerradas; su justificación está en `docs/adr/`.

## 1. Actores

| Actor | Cómo se identifica en el sistema |
|---|---|
| Administrador de plataforma | `User.is_superuser = True`. Trabaja desde **Django Admin**, sin UI propia en Angular. |
| Propietario (OWNER) | `Membership.role = OWNER` en una organización. |
| Gestor (MANAGER) | `Membership.role = MANAGER`. |
| Personal de acceso (STAFF) | `Membership.role = STAFF` + asignado a eventos concretos (`EventStaff`). |
| Asistente | Cualquier usuario registrado. No necesita pertenecer a ninguna organización. |
| Visitante | Usuario no autenticado. Solo puede ver eventos publicados. |

Un mismo usuario puede ser asistente y, a la vez, miembro de una o varias organizaciones con roles distintos.

## 2. Recorridos de usuario

### R1 — Organizador crea y publica un evento
1. Se registra (email + contraseña) e inicia sesión.
2. Crea una organización → se convierte automáticamente en OWNER.
3. Crea un evento (queda en **Borrador**).
4. Añade una o más categorías de entrada (General, VIP…) con su cupo.
5. Publica el evento → aparece en el listado público.

### R2 — Asistente reserva una entrada
1. Ve el listado de eventos publicados (sin necesidad de sesión).
2. Abre un evento y ve categorías con plazas disponibles.
3. Elige categoría → si no tiene sesión, se le pide login/registro y vuelve al evento.
4. Confirma la reserva → se genera su entrada.
5. Ve la entrada con el QR en "Mis entradas" (desde el móvil).

### R3 — Asistente cancela
1. En "Mis entradas" pulsa cancelar (si está dentro del plazo).
2. La entrada pasa a cancelada y la plaza vuelve a estar disponible.

### R4 — Personal de acceso valida entradas
1. Inicia sesión desde el móvil.
2. Ve los eventos que tiene asignados y que están en ventana de acceso.
3. Selecciona el evento y abre el escáner (cámara).
4. Escanea un QR → ve un resultado grande y claro (verde / rojo / ámbar).
5. Sigue escaneando.

### R5 — Organizador consulta resultados
1. Abre el dashboard de su organización: eventos, ocupación y accesos.
2. Entra en un evento: ocupación por categoría, listado de asistentes y accesos.
3. Exporta los asistentes a CSV.

## 3. Reglas de negocio

### 3.1 Cuentas 🔒
- RN-01. El login es por **email** (único, sin distinguir mayúsculas). No existe `username`.
- RN-02. **Para reservar hace falta cuenta.** No hay reservas como invitado en el MVP.

### 3.2 Organizaciones y roles 🔒
- RN-03. Quien crea una organización pasa a ser su OWNER.
- RN-04. Una organización debe tener siempre al menos un OWNER.
- RN-05. Solo OWNER añade, quita o cambia el rol de los miembros. Los miembros se añaden por email de un usuario ya registrado (sin invitaciones por email en el MVP).
- RN-06. Toda consulta de datos privados se filtra por la membresía del usuario. Acceder a un recurso de otra organización devuelve **404** (no 403), para no revelar que existe.

### 3.3 Eventos 🔒
- RN-07. Estados almacenados: `DRAFT` → `PUBLISHED` → `CANCELLED`. No se puede volver a borrador desde publicado.
- RN-08. "Finalizado" **no se guarda**: un evento publicado está finalizado cuando `end_at < ahora`.
- RN-09. Para publicar hace falta: `start_at` en el futuro, `end_at > start_at` y al menos una categoría de entrada.
- RN-10. Cancelar un evento cancela todas sus reservas y entradas no usadas.
- RN-11. Un evento publicado se puede editar (título, descripción, ubicación, imagen, fechas futuras), pero su aforo no puede bajar por debajo de lo ya reservado.

### 3.4 Aforo y categorías 🔒
- RN-12. Cada categoría (`TicketType`) tiene su cupo (`capacity`).
- RN-13. La suma de los cupos de las categorías **no puede superar** `Event.capacity`. Con esto, respetar el cupo de cada categoría garantiza el aforo total y solo hay que proteger un contador.
- RN-14. El cupo de una categoría no puede bajar por debajo de `reserved_count`.
- RN-15. No se puede borrar una categoría que tenga reservas (activas o históricas).

### 3.5 Reservas 🔒
- RN-16. Una reserva = **una entrada**.
- RN-17. Un usuario solo puede tener **una reserva confirmada por evento**. Esto, al estar garantizado en la base de datos, también evita duplicados por doble clic.
- RN-18. Se puede reservar si el evento está publicado, no ha empezado y la categoría tiene plazas.
- RN-19. La reserva es **atómica y segura ante concurrencia**: nunca se supera el cupo, aunque lleguen N peticiones a la vez.

### 3.6 Cancelaciones 🔒
- RN-20. El asistente puede cancelar su reserva hasta **2 horas antes** de `start_at` (`CANCELLATION_DEADLINE_HOURS`, configurable).
- RN-21. OWNER o MANAGER pueden cancelar cualquier reserva de su evento en cualquier momento antes de que termine.
- RN-22. Una entrada ya utilizada no se puede cancelar.
- RN-23. Cancelar libera la plaza (decrementa `reserved_count`).
- RN-24. Una reserva cancelada no se reactiva; el asistente puede volver a reservar si quedan plazas.

### 3.7 Entradas y QR 🔒
- RN-25. Cada entrada tiene un **token opaco aleatorio** (`secrets.token_urlsafe(32)`), único.
- RN-26. El QR contiene **solo el token**: sin datos personales ni IDs.
- RN-27. Estados de entrada: `VALID`, `USED`, `CANCELLED`.

### 3.8 Check-in 🔒
- RN-28. Pueden validar entradas: el STAFF asignado al evento, y OWNER o MANAGER de la organización.
- RN-29. Ventana de acceso: desde **3 horas antes** de `start_at` hasta `end_at` (`CHECKIN_OPENS_HOURS_BEFORE`, configurable).
- RN-30. La validación es atómica: dos escaneos simultáneos de la misma entrada producen un `VALID` y un `ALREADY_USED`.
- RN-31. **Todo intento se registra** en `CheckInLog`, también los fallidos.
- RN-32. Resultados posibles:

| Resultado | Cuándo | Color UI |
|---|---|---|
| `VALID` | Entrada válida del evento → pasa a `USED` | Verde |
| `ALREADY_USED` | Ya validada antes (se muestra cuándo) | Ámbar |
| `CANCELLED` | Entrada cancelada | Rojo |
| `NOT_FOUND` | El token no existe | Rojo |
| `WRONG_EVENT` | Entrada de otro evento | Rojo |
| `EVENT_NOT_ACTIVE` | Fuera de la ventana de acceso o evento cancelado | Rojo |
| `UNAUTHORIZED` | El usuario no puede validar en este evento | Rojo (HTTP 403) |

## 4. Matriz de permisos

| Acción | Visitante | Asistente | STAFF | MANAGER | OWNER |
|---|:-:|:-:|:-:|:-:|:-:|
| Ver eventos publicados | ✅ | ✅ | ✅ | ✅ | ✅ |
| Reservar / ver y cancelar sus entradas | – | ✅ | ✅ | ✅ | ✅ |
| Ver datos privados de la organización | – | – | Solo eventos asignados | ✅ | ✅ |
| Crear, editar, publicar y cancelar eventos | – | – | – | ✅ | ✅ |
| Gestionar categorías | – | – | – | ✅ | ✅ |
| Asignar STAFF a eventos | – | – | – | ✅ | ✅ |
| Ver asistentes, stats y exportar CSV | – | – | – | ✅ | ✅ |
| Validar entradas | – | – | Eventos asignados | ✅ | ✅ |
| Gestionar miembros y editar la organización | – | – | – | – | ✅ |

## 5. Requisitos no funcionales

- RNF-01. Responsive: todo usable a 360 px de ancho.
- RNF-02. PWA instalable (manifest + service worker para los recursos estáticos). La validación requiere conexión.
- RNF-03. Todos los permisos se comprueban en el backend.
- RNF-04. Fechas guardadas en UTC (`USE_TZ=True`) y mostradas en la zona horaria del navegador.
- RNF-05. Throttling en login, reservas y check-in.
- RNF-06. API documentada con OpenAPI (Swagger UI en `/api/docs/`).
- RNF-07. `docker compose up` levanta todo con datos de demostración.
- RNF-08. CI en GitHub Actions: lint + tests de backend (contra PostgreSQL) + tests de frontend.
- RNF-09. Coste 0 €.

## 6. Fuera del MVP

Reservas como invitado, varias entradas por reserva, invitaciones por email, emails transaccionales, pagos, listas de espera, asientos numerados, transferencia de entradas, validación offline, Wallet, despliegue público (opcional al final).
