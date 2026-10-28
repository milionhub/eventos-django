import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, resource } from '@angular/core';

import { Api } from '../../api/api';
import { healthRetrieve } from '../../api/fn/health/health-retrieve'; // not the index: see AuthService
import { Health } from '../../api/models';

type HealthStatus = 'loading' | 'ok' | 'database-down' | 'api-down';

const LABELS: Record<HealthStatus, string> = {
  loading: 'Comprobando el servidor…',
  ok: 'API y base de datos operativas',
  'database-down': 'Base de datos no disponible',
  'api-down': 'Sin conexión con la API',
};

/** Small status light in the footer, fed by /health/. */
@Component({
  selector: 'app-api-status',
  template: `
    <span class="status" role="status" [attr.data-status]="status()">
      <span class="dot" aria-hidden="true"></span>{{ label() }}
    </span>
  `,
  styles: `
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--mat-sys-outline);
    }

    [data-status='ok'] .dot {
      background: #3ddc84;
    }

    [data-status='database-down'] .dot {
      background: #ffb547;
    }

    [data-status='api-down'] .dot {
      background: var(--mat-sys-error);
    }
  `,
})
export class ApiStatus {
  private readonly api = inject(Api);

  private readonly health = resource({
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
  protected readonly label = computed(() => LABELS[this.status()]);
}
