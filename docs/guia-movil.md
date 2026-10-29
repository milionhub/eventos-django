# Guía: probar el escáner en un móvil real

Con esta guía validas una entrada **escaneando su QR con la cámara de tu móvil**, igual que haría el personal en la puerta de un evento.

Tiempo estimado: 15 minutos.

---

## Por qué hace falta un túnel

El navegador del móvil **solo deja usar la cámara en páginas HTTPS** (o en `localhost`, que en el móvil no sirve: ahí `localhost` es el propio teléfono).

Tu servidor de desarrollo es `http://localhost:4200`, sin HTTPS y visible solo desde tu PC. **cloudflared** soluciona las dos cosas: crea gratis una dirección pública del tipo `https://algo-raro.trycloudflare.com` y reenvía todo lo que llega ahí a tu `localhost:4200`.

```
Móvil ──HTTPS──▶ Cloudflare ──túnel──▶ tu PC :4200 (Angular) ──proxy /api──▶ :8000 (Django)
```

El móvil no necesita estar en tu misma wifi: basta con que tenga internet.

> ⚠️ **Seguridad.** Mientras el túnel está abierto, **cualquiera que conozca la dirección puede abrir tu aplicación**, y Django está en modo `DEBUG` (las páginas de error muestran código y configuración). La dirección es aleatoria y difícil de adivinar, pero **no la compartas y cierra el túnel en cuanto termines** (paso 9).

---

## Paso 0 — Preparación (solo la primera vez)

### 0.1 Permitir el dominio del túnel en Django

Django rechaza (error 400 «Bad Request») las peticiones cuyo `Host` no está en `ALLOWED_HOSTS`. El proxy de Angular reenvía el `Host` original, que será `algo-raro.trycloudflare.com`.

1. Abre el archivo **`.env`** de la raíz del proyecto (no `.env.example`).
2. Busca la línea `DJANGO_ALLOWED_HOSTS` y añade `,.trycloudflare.com` al final:

   ```env
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com
   ```

   El punto inicial de `.trycloudflare.com` significa «este dominio y cualquier subdominio». Hace falta porque la dirección del túnel cambia cada vez que lo abres.
3. Guarda el archivo.

### 0.2 Angular (ya está hecho)

El servidor de desarrollo de Angular (Vite) también rechaza los hosts desconocidos. En `frontend/angular.json` ya está permitido:

```json
"allowedHosts": [".trycloudflare.com"]
```

No tienes que hacer nada. Si alguna vez ves la página «Blocked request. This host is not allowed», es esto.

---

## Paso 1 — Arrancar todo en el PC

Abre **tres terminales** en VS Code (`Terminal → New Terminal`, o `Ctrl+Shift+ñ`).

**Terminal 1 — base de datos** (Docker Desktop tiene que estar abierto):

```powershell
cd C:\dev\eventos-django
docker compose up -d db
```

**Terminal 1 (otra vez) — backend:**

```powershell
cd C:\dev\eventos-django\backend
uv run python manage.py runserver
```

Espera a ver `Starting development server at http://127.0.0.1:8000/`.

> Si Django ya estaba arrancado **antes** de editar `.env`, páralo con `Ctrl+C` y vuelve a arrancarlo: el `.env` solo se lee al arrancar.

**Terminal 2 — frontend:**

```powershell
cd C:\dev\eventos-django\frontend
npm start
```

Espera a ver `Local: http://localhost:4200/`.

> Si ya tenías `npm start` arrancado de antes, **reinícialo** (`Ctrl+C` y `npm start`): el cambio de `angular.json` solo se aplica al arrancar.

**Terminal 3 — túnel:**

```powershell
cloudflared tunnel --url http://localhost:4200
```

Tarda unos segundos. Busca en la salida un recuadro como este:

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://palabras-al-azar-1234.trycloudflare.com                                           |
+--------------------------------------------------------------------------------------------+
```

Esa `https://….trycloudflare.com` es **tu dirección para el móvil**. Cópiala. Los mensajes `INF`/`WRN` que siguen son normales; deja esta terminal abierta.

> Si sale `cloudflared: command not found`, cierra y vuelve a abrir VS Code (la instalación con winget cambió el `PATH`). Como alternativa: `& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:4200`.

**Comprobación rápida en el PC:** abre esa dirección en el navegador del PC. Debe salir la página de inicio de 4events. Si da error 1033 o «no se puede acceder», espera 20-30 segundos y recarga.

---

## Paso 2 — Crear un evento de prueba (en el PC, como José)

La puerta de un evento solo está abierta **desde 3 horas antes del inicio hasta el final** (RN-29). Por eso el evento de prueba tiene que empezar dentro de poco.

1. En el PC, abre `http://localhost:4200` e inicia sesión como **José** (`jose.nunez@example.com`, propietario de Sala Apolo).
2. Menú **Organizaciones** → **Sala Apolo** → **Eventos** → botón **Nuevo evento**.
3. Rellena:
   - **Título:** `Prueba móvil`
   - **Ubicación:** `Sala Apolo, Barcelona`
   - **Día de inicio:** hoy
   - **Hora de inicio:** dentro de 1 hora (si son las 10:15, pon `11:15`)
   - **Día de fin:** hoy · **Hora de fin:** 2 horas después del inicio (o usa los botones de **Duración**)
   - **Aforo total:** `10`
4. Pulsa **Crear borrador**. Entras en la página de gestión del evento.
5. Baja hasta el recuadro **Nueva categoría**: nombre `General`, cupo `10` → **Añadir categoría**.
6. Pulsa **Publicar** (arriba).
7. **Cierra sesión** (menú → **Cerrar sesión**).

---

## Paso 3 — Reservar una entrada (en el PC, como Laura)

1. Inicia sesión como **Laura** (`laura.demo@example.com`).
2. En la página de inicio, abre **Prueba móvil**.
3. Pulsa **Reservar gratis**.
4. Ve a **Mis entradas** → abre la entrada de **Prueba móvil**. Se ve el **código QR** con el estado «Válida».
5. **Deja esta pantalla abierta** en el PC. Sube el brillo y, si quieres, haz zoom (`Ctrl` + `+`) para que el QR se vea grande.

---

## Paso 4 — Abrir la aplicación en el móvil

1. En el móvil, abre **Chrome** (Android) o **Safari** (iPhone).
2. Escribe la dirección del túnel del paso 1: `https://….trycloudflare.com`.
   Truco: pásatela por WhatsApp o correo a ti mismo y tócala.
3. Inicia sesión como **José** (en el móvil, el menú está en el icono ☰ de arriba).

---

## Paso 5 — Abrir el escáner

1. Menú ☰ → **Validar**.
2. Aparece **Prueba móvil** con la etiqueta verde **Puerta abierta**. Tócala.

   > Si en su lugar pone «Abre …», el evento empieza dentro de más de 3 horas: edita la hora de inicio (paso 2).

3. El navegador pide **permiso para usar la cámara** → **Permitir**.
4. Se activa la cámara trasera. Si se abre la delantera, toca el botón de **cambiar de cámara** (icono 🔄 en la esquina).

> Si pone «Sin permiso para usar la cámara», el permiso se ha denegado. Para volver a darlo:
> - **Chrome Android:** toca el icono a la izquierda de la dirección → **Permisos** → **Cámara** → Permitir. Recarga.
> - **Safari iPhone:** botón **aA** de la barra de direcciones → **Ajustes del sitio web** → **Cámara** → Permitir. Recarga.

---

## Paso 6 — Primer escaneo: entrada válida ✅

1. Apunta el móvil al QR de la pantalla del PC, encuadrándolo dentro del marco.
2. En cuanto lo lee, la pantalla se pone **verde a pantalla completa** con:
   - **Válida**
   - **Laura** (nombre de la titular) y **General** (la categoría)
3. En Android, el móvil **vibra**. En iPhone no: Safari no permite la vibración desde páginas web.
4. Toca la pantalla para volver al escáner. En la cabecera, el contador pasa a **1 / 1 dentro**, y en **Últimos escaneos** aparece la entrada.

En el PC, recarga la entrada de Laura: ahora sale con el sello **Utilizada** y la hora de entrada.

---

## Paso 7 — Segundo escaneo: ya utilizada ⛔

1. Vuelve a apuntar al mismo QR. Si en el PC ya sale con el sello «Utilizada», sigue siendo el mismo código.
2. La pantalla se pone **ámbar**: **Ya utilizada**, con el nombre y **«Entró a las HH:MM»**. Vibra con un patrón distinto (dos toques).

**Esto es lo que demuestra la fase:** una entrada no se puede usar dos veces. El backend lo garantiza con un `UPDATE` condicional (solo pasa de `VALID` a `USED` si sigue en `VALID`), así que daría igual aunque dos personas la escanearan en el mismo instante desde dos móviles.

---

## Paso 8 (opcional) — Otros casos

| Prueba | Cómo | Resultado esperado |
|---|---|---|
| QR de otro evento | Escanea una entrada de otro evento (por ejemplo, una de Laura para *Noche de Jazz en Apolo*) | **Es de otro evento** (rojo) |
| Código inventado | Escribe `hola` en **¿No lee el QR?** → **Validar** | **Entrada no válida** (rojo) |
| Entrada cancelada | Con tu cuenta (`juan@gmail.com`) reserva en *Prueba móvil*, haz una captura del QR, cancela la entrada y escanea la captura (una entrada cancelada ya no muestra QR) | **Entrada cancelada** (rojo) |

---

## Paso 9 — Terminar

1. En la **terminal 3** (cloudflared) pulsa `Ctrl+C`. La dirección deja de funcionar al momento.
2. Si quieres dejar limpia la base de datos de desarrollo: como José, abre **Prueba móvil** → **Cancelar evento** → **¿Seguro? Cancelar evento**.
3. Puedes dejar `,.trycloudflare.com` en tu `.env`: sin túnel abierto no hace nada.

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| «Blocked request. This host is not allowed» | Angular arrancado antes del cambio de `angular.json` | Reinicia `npm start` |
| La web carga, pero el login falla o salen errores de red | Django responde 400 porque falta `.trycloudflare.com` en `.env`, o no se ha reiniciado | Paso 0.1 y reinicia `runserver` |
| Error 1033 / 502 de Cloudflare | El túnel aún se está propagando, o `npm start` no está arrancado | Espera 30 s; comprueba la terminal 2 |
| El QR no se lee | Reflejos o QR pequeño en la pantalla | Sube el brillo, haz zoom en el PC, inclina un poco el móvil |
| Siempre sale «Fuera de horario» | El evento empieza dentro de más de 3 horas, o ya terminó | Ajusta las horas del evento |
| La dirección del túnel ya no funciona | Cada `cloudflared tunnel --url …` crea una dirección nueva | Usa la que sale en la ejecución actual |
