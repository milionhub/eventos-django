import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, resource } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

import { Api } from '../../core/api/api';
import { healthRetrieve } from '../../core/api/functions';
import { Health } from '../../core/api/models';

type HealthStatus = 'loading' | 'ok' | 'database-down' | 'api-down';

/** Placeholder landing page. Becomes the public events list in Phase 2. */
@Component({
  selector: 'app-home',
  imports: [MatIconModule],
  templateUrl: './home.html',
  styleUrl: './home.scss',
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
