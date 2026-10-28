import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found',
  imports: [RouterLink, MatButtonModule],
  template: `
    <p class="code display" aria-hidden="true">404</p>
    <h1>Página no encontrada</h1>
    <p class="hint">
      Esta entrada no te lleva a ningún sitio. Revisa la dirección o vuelve al inicio.
    </p>
    <a mat-flat-button routerLink="/">Volver al inicio</a>
  `,
  styles: `
    :host {
      display: block;
      padding: 48px 0;
    }

    .code {
      color: var(--app-accent);
      font-size: clamp(6rem, 22vw, 11rem);
    }

    .hint {
      max-width: 30rem;
      margin: 0 0 24px;
      color: var(--mat-sys-on-surface-variant);
    }
  `,
})
export class NotFound {}
