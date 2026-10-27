# Wireframes (baja fidelidad, móvil primero)

> Son bocetos de estructura, no de diseño visual. La UI final usará componentes de Angular Material.

## Mapa de pantallas

| Ruta | Pantalla | Acceso |
|---|---|---|
| `/` | Listado de eventos públicos | Público |
| `/events/:slug` | Detalle del evento + reserva | Público (reservar requiere login) |
| `/login`, `/register` | Auth | Público |
| `/me/tickets` | Mis entradas | Autenticado |
| `/me/tickets/:id` | Entrada con QR | Autenticado (propietario) |
| `/org` | Mis organizaciones / crear | Autenticado |
| `/org/:org` | Dashboard de la organización | MANAGER+ |
| `/org/:org/events/new`, `/org/:org/events/:id` | Formulario y gestión de evento (pestañas) | MANAGER+ |
| `/org/:org/members` | Miembros | OWNER |
| `/checkin` | Eventos donde puedo validar | STAFF+ |
| `/checkin/:eventId` | Escáner | STAFF+ |

---

## Listado público `/`
```
┌──────────────────────────┐
│ ☰  eventos      [Entrar] │
├──────────────────────────┤
│ [🔍 Buscar eventos     ] │
│ ┌──────────────────────┐ │
│ │ [ imagen ]           │ │
│ │ Concierto Jazz       │ │
│ │ 📅 15 nov · 20:00    │ │
│ │ 📍 Sala Apolo        │ │
│ │ 🎟 42 plazas libres  │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │ ...                  │ │
└──────────────────────────┘
```

## Detalle y reserva `/events/:slug`
```
┌──────────────────────────┐
│ ←  Concierto Jazz        │
│ [      imagen          ] │
│ 📅 15 nov 20:00–23:00    │
│ 📍 Sala Apolo            │
│ Descripción...           │
├──────────────────────────┤
│ Entradas                 │
│ ○ General   · 30 libres  │
│ ○ VIP       · 2 libres   │
│ ○ Palco     · AGOTADO    │
│                          │
│ [   Reservar gratis    ] │  ← sin sesión: "Inicia sesión para reservar"
└──────────────────────────┘
  Errores: "Agotado" · "Ya tienes una reserva para este evento"
```

## Entrada `/me/tickets/:id`
```
┌──────────────────────────┐
│ ←  Mi entrada            │
│   Concierto Jazz         │
│   15 nov · 20:00         │
│   General                │
│  ┌────────────────────┐  │
│  │ ▓▓  ▓ ▓▓▓  ▓  ▓▓   │  │
│  │ ▓ ▓▓  ▓  ▓▓▓ ▓ ▓   │  │   QR grande, fondo blanco,
│  │ ▓▓▓ ▓  ▓▓ ▓  ▓▓▓   │  │   se sube el brillo si es posible
│  └────────────────────┘  │
│  Estado: ✅ VÁLIDA       │
│  Laura Gómez              │
│                          │
│ [ Cancelar reserva ]     │  ← oculto fuera de plazo
└──────────────────────────┘
```

## Escáner `/checkin/:eventId`
```
┌──────────────────────────┐
│ ←  Concierto Jazz        │
│ Accesos: 128 / 300       │
│ ┌──────────────────────┐ │
│ │                      │ │
│ │    [ cámara ]        │ │
│ │     ┌──────┐         │ │
│ │     │      │         │ │
│ │     └──────┘         │ │
│ └──────────────────────┘ │
└──────────────────────────┘
       tras escanear ▼
┌──────────────────────────┐
│██████████████████████████│  fondo VERDE / ÁMBAR / ROJO a pantalla completa
│        ✔ VÁLIDA          │  + vibración del móvil
│      Laura Gómez          │
│        General           │
│  (se cierra en 2 s o al  │
│        tocar)            │
└──────────────────────────┘
  ÁMBAR: "YA UTILIZADA · 20:14 por Ana"
  ROJO: "CANCELADA" / "NO EXISTE" / "OTRO EVENTO" / "FUERA DE HORARIO"
```

## Gestión de evento `/org/:org/events/:id` (escritorio)
```
┌──────────┬──────────────────────────────────────────────┐
│ Org ▾    │ Concierto Jazz         [BORRADOR] [Publicar] │
│ Dashboard│ ┌ Datos ┬ Entradas ┬ Staff ┬ Asistentes ┬ Stats ┐
│ Eventos  │ │                                            │
│ Miembros │ │ Entradas                     [+ Categoría] │
│ Check-in │ │ Nombre    Cupo  Reservadas  Acciones       │
│          │ │ General   250   208  ████▒  ✎ 🗑           │
│          │ │ VIP        50    48  █████  ✎              │
│          │ │ Total: 300 / aforo 300                     │
└──────────┴──────────────────────────────────────────────┘
  Asistentes: tabla con búsqueda y filtro de estado, [Exportar CSV]
```

## Dashboard `/org/:org`
```
┌───────────┬───────────┬───────────┬───────────┐
│ Eventos   │ Reservas  │ Ocupación │ Accesos   │
│ activos 4 │ 812       │ 73 %      │ 340       │
└───────────┴───────────┴───────────┴───────────┘
 Próximos eventos
 Evento          Fecha     Ocupación     Accesos
 Concierto Jazz  15 nov    ████████░ 85%  —
 Charla Django   20 nov    ███░░░░░░ 31%  —
```
