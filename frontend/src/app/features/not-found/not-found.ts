import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found',
  imports: [RouterLink, MatButtonModule],
  template: `
    <h1>Página no encontrada</h1>
    <p>La página que buscas no existe.</p>
    <a mat-flat-button routerLink="/">Volver al inicio</a>
  `,
})
export class NotFound {}
