# Identidad visual — #4events

Dirección: **"Noche de concierto"**. La app tiene que parecer un cartel de concierto, no un panel de administración: fondo oscuro, titulares grandes y un único acento coral que se usa con moderación.

## Marca
- **Nombre:** `#4events`. La almohadilla va siempre en coral (`.hash`).
- **Favicon:** `frontend/public/favicon.svg`, una entrada coral con la almohadilla.

## Color
El tema se genera con Angular Material 3 a partir de tres colores semilla (`src/styles/_theme-colors.scss`, creado con `ng generate @angular/material:theme-color`):

| Rol | Semilla | Uso |
|---|---|---|
| Primario | `#FF5A4E` coral | Acciones principales, acentos, foco |
| Terciario | `#8B6CFF` violeta | Reservado para destacar estados secundarios |
| Neutro | `#17151D` tinta | Fondos, superficies y texto |

Ajustes sobre el tema generado (`styles.scss`):
- En oscuro, el primario es el coral puro con texto casi negro encima (contraste AA). En claro se usa el tono 40 (`#B52420`) para que el texto coral sea legible sobre blanco.
- El texto secundario y los bordes usan la paleta neutra, no la derivada del coral (si no, salen rosados).

**Tema oscuro por defecto.** El usuario puede cambiar a claro desde la cabecera y la elección se guarda en `localStorage` (`ThemeService`). Material usa `light-dark()`, así que cambiar `color-scheme` cambia toda la paleta.

Colores de estado (puntos y avisos): verde `#3DDC84` correcto · ámbar `#FFB547` aviso · `--mat-sys-error` error. Coinciden con los colores del escáner (RN-32).

## Tipografía
| Uso | Fuente | Notas |
|---|---|---|
| Titulares y marca | **Bricolage Grotesque** 600–800 | `h1`–`h3` y la clase `.display` (mayúsculas, peso 800, interlineado apretado) |
| Texto | **Inter** 400–600 | Todo lo demás, a través de la tipografía de Material |

Ambas son gratuitas (Google Fonts).

## Tokens propios
Definidos en `styles.scss` y disponibles en cualquier componente:

| Token | Valor |
|---|---|
| `--app-accent` | Coral (más oscuro en tema claro) |
| `--app-font-display` | Bricolage Grotesque |
| `--app-radius` / `--app-radius-sm` | 16px / 8px |
| `--app-border` | 1px con `outline-variant` |

Para el resto se usan los tokens de sistema de Material (`--mat-sys-surface-container`, `--mat-sys-on-surface-variant`…). Nada de colores sueltos en los componentes.

## Motivo: la entrada troquelada
Las tarjetas que representan eventos o entradas tienen forma de entrada física: dos muescas laterales y una línea de corte discontinua que separa el "talón". Se hace con los mixins de `src/styles/_ticket.scss`:

```scss
@use 'ticket';

.card { @include ticket.notched($at: 72%); }
.card-tear { @include ticket.tear-line; }
```

Úsalo para eventos y entradas; no para formularios ni tablas.

## Formularios
- Campos `outline` con esquinas de 12px; el borde y la etiqueta se vuelven coral al enfocar.
- Icono a la izquierda (`matPrefix`) que dice qué se escribe, y ayudas (`mat-hint`) con ejemplos o el efecto del dato (duración del evento, dirección de la organización, plazas que quedan).
- Formularios largos en **secciones numeradas** (`.form-section`): título y explicación a la izquierda, campos a la derecha; en móvil, apilados.
- Acciones en una barra fija al final (`.form-actions`), con aviso de cambios sin guardar.
- Formularios cortos dentro de una página (añadir miembro, nueva categoría): cabecera con icono en una pastilla coral, título y una línea de ayuda.
- Crear un evento muestra al lado la **vista previa** de la tarjeta pública (`app-event-ticket`), la misma que ve el público.
- **Fechas:** calendario de Material para el día (campo de solo lectura: se elige en el calendario, nunca se escribe) y selector de hora en pasos de 15 min (sí se puede escribir, «20:30»). Día y hora son controles separados; botones de duración rápida para el fin.
- **Imágenes:** `app-image-picker`: zona para arrastrar o elegir, vista previa en formato cartel 16:9 y control de encuadre. Recorta en el navegador; el backend valida y re-codifica igualmente ([ADR-0008](adr/0008-subida-de-imagenes.md)).

## Clases globales
- `.display`: titular tipo cartel.
- `.eyebrow`: etiqueta pequeña en mayúsculas y coral, encima de un titular.
- `.lead`: párrafo de introducción bajo el titular.
- `.surface-card`: superficie elevada para tarjetas y paneles.
- `.chip`: etiqueta en forma de píldora (roles, estados). Con `data-status="DRAFT|PUBLISHED|CANCELLED|FINISHED"` toma el color del estado del evento.
- `.back-link`: enlace "← Volver" encima del titular.
- `.notice` / `.notice.error`: aviso tras una acción (éxito o error).
- `.quiet`: botón de texto secundario (Editar, Quitar…), gris; con `.confirming` se vuelve rojo mientras pide confirmación.

Las fechas formateadas pasan por el pipe `capitalize` (solo la primera letra): `text-transform: capitalize` pondría "Sábado 12 De Diciembre".

## Reglas
- Un único acento por pantalla: el coral marca la acción principal; el resto, en neutros. Las acciones secundarias ("Quitar", "Cancelar") van en gris y solo se vuelven rojas al pedir confirmación.
- Todo usable a 360 px (RNF-01) y con foco visible (`:focus-visible` en coral).
- Las animaciones se desactivan con `prefers-reduced-motion`.
