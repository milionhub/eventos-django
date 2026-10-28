import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, resource } from '@angular/core';

import { Api } from '../../core/api/api';
import { healthRetrieve } from '../../core/api/functions';
import { Health } from '../../core/api/models';

type HealthStatus = 'loading' | 'ok' | 'database-down' | 'api-down';

/** Placeholder landing page. Becomes the public events list in Phase 2. */
@Component({
  selector: 'app-home',
  template: `
    <h1>Próximos eventos</h1>
    <p>Aquí aparecerán los eventos publicados.</p>

    <p class="health" role="status" [attr.data-status]="status()">
      @switch (status()) {
        @case ('loading') {
          Comprobando el estado del servidor…
        }
        @case ('ok') {
          API y base de datos operativas.
        }
        @case ('database-down') {
          La API responde, pero la base de datos no está disponible.
        }
        @case ('api-down') {
          No se puede conectar con la API.
        }
      }
    </p>
  `,
  styles: `
    .health {
      color: var(--mat-sys-on-surface-variant);
      font: var(--mat-sys-body-small);
    }
  `,
})
export class Home {
  private readonly api = inject(Api);

  protected readonly health = resource({
    loader: async (): Promise<Health> => {
      try {
        return await this.api.invoke(healthRetrieve);
      } catch (error) {
        // The backend answers 503 with the same body when the database is down.
        if (error instanceof HttpErrorResponse && error.status === 503) {
          return error.error as Health;
        }
        throw error;
      }
    },
  });

  protected readonly status = computed<HealthStatus>(() => {
    if (this.health.isLoading()) return 'loading';
    if (this.health.error() || !this.health.hasValue()) return 'api-down';
    return this.health.value().database ? 'ok' : 'database-down';
  });
}
