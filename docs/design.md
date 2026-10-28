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

## Clases globales
- `.display`: titular tipo cartel.
- `.eyebrow`: etiqueta pequeña en mayúsculas y coral, encima de un titular.

## Reglas
- Un único acento por pantalla: el coral marca la acción principal; el resto, en neutros.
- Todo usable a 360 px (RNF-01) y con foco visible (`:focus-visible` en coral).
- Las animaciones se desactivan con `prefers-reduced-motion`.
