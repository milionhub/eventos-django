# Seguridad — revisión de la Fase 6

Revisión del backend hecha el 2026-10-29 (Fase 6, bloque 2). Para cada punto: qué se comprobó, qué se encontró y qué se hizo. Lo que queda abierto está en la [última sección](#riesgos-aceptados-y-pendientes).

## Resumen

| Punto | Resultado |
|---|---|
| Aislamiento entre organizaciones | ✅ Correcto. 4 vistas validaban el cuerpo antes de buscar el objeto: sin fuga, pero corregido |
| IDs enumerables | ✅ Correcto, sin cambios |
| Throttling | ⚠️ **Se podía saltar** con `X-Forwarded-For`. Corregido. Añadido también en registro y refresh |
| Configuración de producción | ⚠️ Faltaban HSTS y la redirección a HTTPS. Añadidas, y comprobadas en la CI |
| Cabeceras | ✅ Añadida una CSP estricta para la API |
| `DEBUG` y secretos | ✅ Correcto, sin cambios |
| Dependencias | ✅ Sin vulnerabilidades conocidas (bloque 1, comprobado cada lunes en la CI) |

## Aislamiento entre organizaciones

**Regla:** pedir algo de otra organización devuelve 404, nunca 403. Un 403 confirmaría que el recurso existe.

**Cómo se comprueba:** [`core/tests/test_isolation.py`](../backend/apps/core/tests/test_isolation.py) recorre **todas las rutas** que cuelgan de `organizations/{org}/`, leídas del `urlconf`, con todos sus métodos. Hay dos tipos de intruso, ambos OWNER de otra organización:
1. Pide las URLs de la organización víctima: 404.
2. Pide las URLs de **su propia** organización, pero con los ids de la víctima (evento, categoría, miembro, staff, reserva): 404.

Después de cada petición se comprueba que no ha cambiado nada: el evento sigue publicado, la entrada sigue válida, etc. El test cubre también el escáner (`checkin/events/{id}/…`) y las entradas y reservas de otra persona (`me/tickets/…`, `reservations/…/cancel/`).

Las rutas no están escritas a mano en el test: **un endpoint nuevo queda cubierto el mismo día que se añade**. Si usa un parámetro de URL que el test no conoce, el test falla hasta que se le enseña.

**¿Detecta los fallos?** Se probó quitando el filtro por organización de `events.selectors.event_of`: fallaron 17 casos.

**Hallazgo:** 4 vistas validaban el cuerpo de la petición antes de buscar el objeto, así que con un cuerpo vacío respondían 400 en vez de 404:
- `PATCH members/{id}/`
- `PUT events/{id}/image/`
- `POST events/{id}/ticket-types/`
- `POST events/{id}/staff/`

No era una fuga: el 400 salía igual existiera el id o no, y con un cuerpo válido respondían 404. Pero que no hubiera fuga dependía de que ninguna validación mirase nunca el objeto. Ahora las cuatro buscan primero (404) y validan después.

## IDs enumerables

| Recurso | Identificador en la URL | ¿Adivinable? | Por qué es aceptable |
|---|---|---|---|
| Organización | slug | Sí | Hay que ser miembro: si no, 404 |
| Evento (organizador) | entero | Sí | Siempre dentro de `organizations/{org}/` y filtrado por esa organización |
| Evento (público) | slug | Sí | Solo eventos publicados; borradores y cancelados dan 404 (con test) |
| Categoría, miembro, staff | entero | Sí | Filtrados por el evento o la organización de la URL |
| Reserva y entrada | UUID v4 | No | Además, filtradas por su dueño |
| Token del QR | `secrets.token_urlsafe(32)` (256 bits) | No | El escáner tiene throttling (120/min) |
| Usuario (en staff) | entero | Sí | `assign_staff` exige que sea miembro de la organización (`not_a_member`) |

Un entero en la URL solo es un problema si basta con cambiarlo para ver algo ajeno, y eso es justo lo que prueba el test de aislamiento.

## Throttling

### Hallazgo: el límite se podía saltar
DRF identifica al cliente por su IP. Con `NUM_PROXIES` sin configurar, como lo teníamos, **usa la cabecera `X-Forwarded-For` entera** si viene en la petición. Esa cabecera la escribe el cliente: mandando un valor distinto en cada intento, el límite de 10 logins por minuto no se aplicaba nunca. El test `test_login_throttle_ignores_a_forged_x_forwarded_for` lo demostró: falló antes del arreglo y pasa después.

**Arreglo:** `NUM_PROXIES` se lee del entorno.
- **0 por defecto:** se ignora la cabecera y se usa la IP de la conexión.
- **Detrás de nginx (Fase 7), 1:** se usa la última entrada de `X-Forwarded-For`, que es la que añade nginx y el cliente no puede falsificar.

### Límites
| Endpoint | Límite | Variable |
|---|---|---|
| Login | 10/min | `THROTTLE_LOGIN_RATE` |
| Registro (nuevo) | 20/hora | `THROTTLE_REGISTER_RATE` |
| Refresh (nuevo) | 30/min (cada carga de página o pestaña refresca una vez) | `THROTTLE_REFRESH_RATE` |
| Reservas | 20/min | `THROTTLE_RESERVATIONS_RATE` |
| Escaneo | 120/min | `THROTTLE_CHECKIN_RATE` |

## Configuración de producción

`manage.py check --deploy` con `config.settings.prod` daba 2 avisos. Ahora no da ninguno, y **la CI lo comprueba en cada cambio**: el paso falla con cualquier aviso; por ejemplo, con una `SECRET_KEY` débil.

- **Redirección a HTTPS** (`SECURE_SSL_REDIRECT`): activada por defecto.
- **HSTS:** empieza en 1 hora (`SECURE_HSTS_SECONDS`). Si se configura mal, los navegadores que ya la hayan guardado no se pueden corregir, así que se sube a un año cuando HTTPS esté comprobado.
- **Sin *preload*:** esa lista es para dominios propios, y con presupuesto 0 € no lo hay. Su aviso (`security.W021`) está silenciado con esa justificación.
- **Demo local por HTTP:** las dos opciones se desactivan con variables de entorno, sin tocar el código.

## Cabeceras

| Cabecera | Valor | Origen |
|---|---|---|
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` | **Nuevo:** [`core/middleware.py`](../backend/apps/core/middleware.py), solo en `/api/v1/` |
| `X-Content-Type-Options` | `nosniff` | Django |
| `X-Frame-Options` | `DENY` | Django |
| `Referrer-Policy` | `same-origin` | Django (valor por defecto) |
| `Cross-Origin-Opener-Policy` | `same-origin` | Django (valor por defecto) |
| `Strict-Transport-Security` | `max-age=3600; includeSubDomains` | Solo en producción |

**CSP sin dependencias.** Django 5.2 no trae CSP propia, y la API solo devuelve datos (JSON, el SVG del QR y el CSV), así que basta con una política fija de 20 líneas. No hace falta `django-csp`. Con ella, ni el SVG abierto directamente en el navegador puede ejecutar nada. Swagger (`/api/docs/`) y el admin se quedan fuera porque cargan scripts. **La CSP de la app Angular** irá en nginx en la Fase 7.

Hay tests en [`core/tests/test_security_headers.py`](../backend/apps/core/tests/test_security_headers.py).

## Autenticación y CSRF

Ya estaba revisado en el [ADR-0003](adr/0003-autenticacion-jwt.md). Se confirma que:
- El **access token** solo vive en memoria (Angular) y caduca a los 15 min.
- El **refresh token** va en una cookie `httpOnly`, `SameSite=Strict` y `Secure` en producción, enviada solo a `/api/v1/auth/`. Rota en cada uso y el anterior se invalida (blacklist).
- **CSRF:** la API se autentica con la cabecera `Authorization`, que un sitio ajeno no puede enviar. Los dos endpoints que usan la cookie (refresh y logout) están protegidos por `SameSite=Strict`, porque el navegador no la manda desde otro sitio.

## `DEBUG` y secretos

- `DEBUG` es `False` por defecto y `prod.py` lo fuerza. La CI comprueba la configuración de producción.
- `DJANGO_SECRET_KEY` es obligatoria: sin ella, Django no arranca.
- `.env` está en `.gitignore` y nunca ha estado en el historial (`git log --all -- .env` no devuelve nada). No hay claves escritas en el código. Las contraseñas de las guías son de cuentas de prueba que se crean durante la propia guía.

## Riesgos aceptados y pendientes

- **Saber si un email ya tiene cuenta.** El registro responde 409 si el email ya existe. Es la experiencia habitual («ya tienes cuenta, entra») y el throttling de registro limita que se use para probar emails en masa. El login no lo revela: responde siempre «Email o contraseña incorrectos».
- **Contadores de throttling por proceso.** Se guardan en la caché por defecto de Django, que es memoria local. Con varios procesos de gunicorn, cada uno lleva su propia cuenta y el límite real se multiplica por el número de procesos. **Para la Fase 7:** caché compartida en la base de datos (`DatabaseCache` + `createcachetable`, sin coste) o un solo proceso en la demo.
- **CSP de la app Angular:** Fase 7, en nginx.
- **El admin de Django** está en `/admin/`. En un despliegue real convendría limitarlo por IP o cambiar la ruta. Se revisa en la Fase 7.
