# Guía: probar la Fase 5 (dashboard, stats, asistentes, CSV, móvil y PWA)

Esta guía recorre todo lo nuevo de la Fase 5 con un **evento de prueba nuevo**, para que cada cifra que tienes que ver en pantalla sea exacta.

Tiempo estimado: 30-40 minutos.

| Parte | Qué pruebas | Dónde |
|---|---|---|
| 0 | Arrancar todo (con el build de producción) | PC |
| 1-2 | Crear el evento y las reservas | PC |
| 3 | Instalar la app y validar una entrada | iPhone |
| 4-6 | Dashboard, stats, asistentes, CSV y cancelación | PC |
| 7 | Permisos | PC |
| 8 | Responsive a 360 px | PC |
| 9 | La app sin conexión | iPhone |
| 10 | Limpiar | PC + iPhone |

Usuarios (contraseña de los dos de demo: la de siempre):

| Quién | Email | Papel en Sala Apolo |
|---|---|---|
| José | `jose.nunez@example.com` | Propietario (OWNER) |
| Laura | `laura.demo@example.com` | Gestora (MANAGER) |
| Tú | `juan@gmail.com` | Ninguno (asistente) |

---

## Parte 0 — Arrancar todo

Igual que en la [guía del móvil](guia-movil.md), pero **el frontend se arranca en modo producción**: la app solo es instalable (PWA) con el build de producción.

**Terminal 1 — base de datos y backend:**

```powershell
cd C:\dev\eventos-django
docker compose up -d db
cd backend
uv run python manage.py runserver
```

**Terminal 2 — frontend en modo producción:**

```powershell
cd C:\dev\eventos-django\frontend
npm start -- --configuration production
```

Espera a `Local: http://localhost:4200/`. Tarda algo más que `npm start`, y los cambios de código no se recargan solos (no los vas a necesitar).

**Terminal 3 — túnel:**

```powershell
cloudflared tunnel --url http://localhost:4200
```

Copia la dirección `https://….trycloudflare.com` que aparece en el recuadro.

> Tu `.env` ya tiene `.trycloudflare.com` en `DJANGO_ALLOWED_HOSTS` de la Fase 4. Si no, mira el paso 0.1 de la guía del móvil.

---

## Parte 1 — Crear el evento (PC, como José)

1. Abre `http://localhost:4200` e inicia sesión como **José**.
2. **Organizaciones** → **Sala Apolo** → **Eventos** → **Nuevo evento**.
3. Rellena:
   - **Título:** `Prueba Fase 5`
   - **Ubicación:** `Sala Apolo, Barcelona`
   - **Día de inicio:** hoy · **Hora de inicio:** dentro de 1 hora
   - **Día de fin:** hoy · **Hora de fin:** 3 horas después del inicio
   - **Aforo total:** `15`
4. **Crear borrador**.
5. Pestaña **Entradas**, en **Nueva categoría**:
   - `General`, cupo `10` → **Añadir categoría**
   - `VIP`, cupo `5` → **Añadir categoría**
6. **Publicar**.
7. **Cerrar sesión**.

---

## Parte 2 — Tres reservas (PC)

Las reservas se hacen en este orden a propósito: la lista de asistentes muestra primero la más reciente.

### 2.1 Juan, en VIP
1. Inicia sesión con **tu cuenta** (`juan@gmail.com`).
2. Inicio → **Prueba Fase 5** → elige **VIP** → **Reservar gratis**.
3. **Cerrar sesión**.

### 2.2 Una cuenta «maliciosa», en General
Esta cuenta sirve para comprobar la protección del CSV (parte 6.4).

1. **Entrar** → al final, «¿No tienes cuenta? **Crea una**» → rellena:
   - **Nombre:** `=HYPERLINK("https://example.com";"Clic")` (cópialo tal cual, con las comillas)
   - **Apellidos:** `Prueba`
   - **Email:** `hacker.prueba@example.com`
   - **Contraseña:** `Concierto-2026`
2. Inicio → **Prueba Fase 5** → **General** → **Reservar gratis**.
3. **Cerrar sesión**.

### 2.3 Laura, en General (y deja su QR a la vista)
1. Inicia sesión como **Laura**.
2. **Prueba Fase 5** → **General** → **Reservar gratis**.
3. **Mis entradas** → abre la de **Prueba Fase 5**. Deja el QR en pantalla, con el brillo alto.

---

## Parte 3 — Instalar la app y validar (iPhone, como José)

### 3.1 Instalar
1. En **Safari**, abre la dirección del túnel.
2. Botón **Compartir** (cuadrado con flecha hacia arriba) → **Añadir a pantalla de inicio** → **Añadir**.
3. En la pantalla de inicio aparece el icono **4events**: un ticket coral con `#` sobre fondo oscuro.
4. **Ábrela desde el icono.** ✅ Debe ocupar toda la pantalla, **sin la barra de direcciones de Safari**.

### 3.2 Validar a Laura
1. Dentro de la app instalada, inicia sesión como **José**.
2. Menú ☰ → **Validar** → **Prueba Fase 5** (etiqueta **Puerta abierta**).
3. Permite la cámara y escanea el QR de Laura en el PC → ✅ **Válida** (verde), Laura · General.
4. Toca para seguir y **escanéalo otra vez** → ✅ **Ya utilizada** (ámbar).

> Si la cámara no arranca dentro de la app instalada, haz este paso en Safari normal (misma dirección). Es una limitación de algunas versiones de iOS, no de la app.

---

## Parte 4 — Dashboard de la organización (PC, como José)

1. En el PC: **Cerrar sesión** (Laura) e inicia sesión como **José**.
2. **Organizaciones** → **Sala Apolo**.

✅ Arriba sale **Resumen** con 4 indicadores: **Eventos activos**, **Reservas**, **Ocupación** (con barra) y **Accesos**. Suman todos los eventos publicados de Sala Apolo, también los de pruebas anteriores, así que los totales no tienen un valor fijo. Comprueba que tienen sentido: si cancelas o reservas algo, cambian.

✅ En **Próximos eventos**, la fila de **Prueba Fase 5** muestra:

| Dato | Valor esperado |
|---|---|
| Porcentaje | **20 %** |
| Reservas / plazas | **3 / 15** |
| Debajo de la barra | **1 dentro** |

3. Haz clic en la fila → te lleva a la gestión del evento.

---

## Parte 5 — Pestaña Stats

1. En la gestión de **Prueba Fase 5**, pestaña **Stats**. La URL termina en `?tab=stats`.
2. ✅ Indicadores:

| Indicador | Valor | Detalle |
|---|---|---|
| Reservas | **3** | de 15 plazas |
| Ocupación | **20 %** | barra al 20 % |
| Dentro | **1** | 33 % de las reservas |
| Canceladas | **0** | reservas anuladas |

3. ✅ **Por categoría:**

| Categoría | Reservadas | Dentro |
|---|---|---|
| General | **2 / 10** | **1 / 2** |
| VIP | **1 / 5** | **0 / 1** |

4. ✅ **Intentos de acceso:** **Válida 1** (icono verde) y **Ya utilizada 1** (icono ámbar) → «**2 escaneos en total**».
5. Recarga la página (`F5`): ✅ sigue abierta la pestaña **Stats** (va en la URL).

---

## Parte 6 — Pestaña Asistentes

Pestaña **Asistentes**.

### 6.1 La lista
✅ 3 reservas, la más reciente primero:

| # | Nombre | Categoría | Estado |
|---|---|---|---|
| 1 | Laura Gomez | General | **Utilizada · HH:MM** (gris) |
| 2 | `=HYPERLINK("https://example.com";"Clic") Prueba` | General | Válida |
| 3 | Juan Marin | VIP | Válida |

✅ La fila 2 enseña el nombre **como texto**: Angular nunca interpreta lo que escribe un usuario como código.
✅ Debajo: «**3 reservas**».

### 6.2 Buscar
Escribe en **Buscar** y espera medio segundo (busca sola, sin pulsar Enter):

| Escribes | Debe salir |
|---|---|
| `laura` | Solo Laura |
| `MARIN` | Solo Juan (no distingue mayúsculas) |
| `laura gomez` | Solo Laura (cada palabra puede estar en un campo distinto) |
| `example` | Laura y la cuenta de prueba (busca también en el email) |
| `zzz` | «Nadie coincide con la búsqueda.» |

Borra la búsqueda.

### 6.3 Filtrar por estado
Desplegable **Entrada**:
- **Utilizada** → ✅ solo Laura.
- **Válida** → ✅ Juan y la cuenta de prueba.
- **Todas** → ✅ las 3.

### 6.4 Exportar CSV
1. Con **Todas** y sin búsqueda, pulsa **Exportar CSV**.
2. ✅ Se descarga `asistentes-prueba-fase-5.csv` (si ya existía un evento con ese nombre, `…-fase-5-2.csv`).
3. Ábrelo con **Excel** (doble clic):
   - ✅ Sale en **columnas** separadas: Nombre, Apellidos, Email, Categoría, Estado, Reservada, Entrada.
   - ✅ Las tildes se ven bien («Categoría», «Válida»).
   - ✅ Las horas son **hora española**, las mismas que en la pantalla.
   - ✅ En la fila de Laura, **Entrada** tiene la hora del escaneo; en las demás está vacía.
4. **La prueba de seguridad:** mira la celda **Nombre** de la cuenta de prueba.
   - ✅ Se ve el **texto** `'=HYPERLINK("https://example.com";"Clic")`, con un apóstrofo delante, y **no un enlace «Clic»**.
   - Ese apóstrofo es la protección: como la celda ya no empieza por `=`, Excel no la ejecuta como fórmula. Sin él, quien se registrara con ese nombre podría colar un enlace malicioso, o algo peor, en el Excel del organizador.
5. Prueba el filtro: elige **Válida** y vuelve a exportar → ✅ el CSV solo tiene a Juan y a la cuenta de prueba.

### 6.5 Cancelar como organizador
1. Vuelve a **Todas**. En la fila de **Juan Marin**, pulsa **Cancelar reserva**.
2. ✅ El botón cambia a **«¿Seguro? Cancelar»** y todavía no ha pasado nada.
3. Púlsalo otra vez → ✅ «**Reserva de Juan Marin cancelada.**» y su estado pasa a **Cancelada** (rojo), sin botón.
4. ✅ Laura (**Utilizada**) no tiene botón de cancelar: una entrada usada no se puede cancelar (RN-22).
5. Pestaña **Stats** → ✅ ahora: **Reservas 2** (de 15), **Ocupación 13 %**, **Dentro 1** (50 % de las reservas), **Canceladas 1**, y **VIP 0 / 5**.
6. Pestaña **Entradas** → ✅ VIP tiene **0 reservadas** y **5 libres**: la plaza ha vuelto.

---

## Parte 7 — Permisos

### 7.1 Laura (gestora) también ve el dashboard
1. Cierra sesión e inicia como **Laura** → **Organizaciones** → **Sala Apolo**.
2. ✅ Ve el **Resumen** y los **Próximos eventos**, igual que José.

### 7.2 El personal de acceso no ve cifras
José es **personal de acceso (STAFF)** en *Jazz Club Malasaña*.

1. Cierra sesión e inicia como **José** → **Organizaciones** → **Jazz Club Malasaña**.
2. ✅ **No** hay Resumen: solo el acceso a **Eventos**.
3. Escribe a mano en la barra de direcciones `http://localhost:4200/org/jazz-club-malasana/events/1?tab=stats` → ✅ te devuelve a **Organizaciones**.

> Esto es solo la interfaz. La protección real está en el backend: la API responde 403 a STAFF y 404 a quien no es de la organización. Lo cubren los tests (`test_stats.py`, `test_attendees.py`).

---

## Parte 8 — Responsive a 360 px (PC)

1. Como José, abre la gestión de **Prueba Fase 5**.
2. Pulsa `F12` → icono de **móvil/tablet** (o `Ctrl+Shift+M`) → arriba, en **Dimensions**, elige **Responsive** y escribe ancho **360**.
3. Comprueba:

| Pantalla | ✅ Qué tiene que pasar |
|---|---|
| Gestión del evento | Las **5 pestañas** (Datos, Entradas, Staff, Asistentes, Stats) caben **sin flechas**. «Entradas» va sin el contador. |
| Cabecera del evento | El icono del reloj va **pegado a la fecha**, no solo en una línea. |
| Asistentes | Cada persona en una tarjeta. La etiqueta de estado tiene su tamaño, sin estirarse. Nada se sale por la derecha. |
| Stats | Indicadores de 2 en 2. Por categoría: el nombre arriba y las dos barras debajo. |
| Sala Apolo (dashboard) | Indicadores de 2 en 2. En próximos eventos, la barra va debajo del título. |

4. En ninguna pantalla debe aparecer **scroll horizontal**: arrastra a la derecha y no debería moverse.
5. Prueba también el modo oscuro (icono 🌙 arriba) en alguna de ellas.

---

## Parte 9 — La app sin conexión (iPhone)

1. Cierra la app instalada del todo (desliza hacia arriba en el selector de apps).
2. Activa el **modo avión**.
3. Abre **4events** desde el icono.
4. ✅ La app **abre**: se ven la cabecera y el diseño, porque sus archivos están guardados en el móvil.
5. ✅ Los datos **no** cargan: salen mensajes de error de carga, y abajo, en el pie, «**Sin conexión con la API**».

   Es lo esperado (RNF-02): la app solo guarda sus propios archivos, **nunca datos de la API**, y validar entradas siempre necesita conexión.
6. Quita el modo avión y recarga → ✅ todo vuelve.

---

## Parte 10 — Limpiar

1. **PC, como José:** **Prueba Fase 5** → **Cancelar evento** → **¿Seguro? Cancelar evento**.
2. **iPhone:** mantén pulsado el icono de **4events** → **Eliminar app**. Cada dirección del túnel es una app distinta: con el próximo túnel la instalada ya no funcionaría.
3. **Terminal 3:** `Ctrl+C` para cerrar el túnel.
4. **Terminal 2:** `Ctrl+C`, y para seguir desarrollando vuelve a `npm start` (sin `--configuration production`).

La cuenta `hacker.prueba@example.com` puedes dejarla: sirve para repetir la prueba del CSV.

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| No aparece «Añadir a pantalla de inicio» o la app abre con barra de Safari | Estás usando `npm start` sin producción, o la añadiste antes de arrancar en producción | Parte 0 (terminal 2) y vuelve a añadirla |
| «Prueba Fase 5» sale con «Abre …» en Validar | El evento empieza dentro de más de 3 horas | Edita la hora de inicio (pestaña Datos) |
| El CSV se abre en Excel todo en una columna | Excel en un idioma que usa coma como separador | **Datos → Desde texto/CSV** y elige punto y coma |
| Exportar CSV está desactivado | La lista filtrada está vacía | Cambia el filtro o borra la búsqueda |
| Los cambios del código no se ven | El build de producción no recarga solo | `Ctrl+C` y vuelve a lanzar el comando de la terminal 2 |
| La app instalada no carga nada tras cerrar el túnel | Apunta a la dirección vieja | Elimínala e instálala con la dirección nueva |
