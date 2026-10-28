import { DatePipe } from '@angular/common';
import { Component, computed, inject, input, resource, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import { eventsList } from '../../../core/api/functions';
import { EventStatusEnum } from '../../../core/api/models';
import { AuthService } from '../../../core/auth/auth.service';
import { CapitalizePipe } from '../../../shared/capitalize.pipe';
import { DateBadge } from '../../../shared/date-badge';
import { eventStatusLabel } from '../../../shared/events';

/** Must match the backend's PAGE_SIZE. */
const PAGE_SIZE = 20;

const FILTERS: { status: EventStatusEnum | null; label: string }[] = [
  { status: null, label: 'Todos' },
  { status: 'DRAFT', label: 'Borradores' },
  { status: 'PUBLISHED', label: 'Publicados' },
  { status: 'CANCELLED', label: 'Cancelados' },
];

/** An organization's events. STAFF see only the ones they are assigned to, read-only. */
@Component({
  selector: 'app-events',
  imports: [
    CapitalizePipe,
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    DateBadge,
  ],
  templateUrl: './events.html',
  styleUrl: './events.scss',
})
export class Events {
  private readonly api = inject(Api);
  private readonly auth = inject(AuthService);

  /** `:org` route parameter. */
  readonly org = input.required<string>();

  protected readonly filters = FILTERS;
  protected readonly statusLabel = eventStatusLabel;
  protected readonly status = signal<EventStatusEnum | null>(null);
  protected readonly page = signal(1);

  protected readonly canManage = computed(() => {
    const role = this.auth.roleIn(this.org());
    return role === 'OWNER' || role === 'MANAGER';
  });

  protected readonly events = resource({
    params: () => ({
      org_slug: this.org(),
      page: this.page(),
      status: this.status() ?? undefined,
    }),
    loader: ({ params }) => this.api.invoke(eventsList, params),
  });

  protected readonly pages = computed(() =>
    Math.max(1, Math.ceil((this.events.value()?.count ?? 0) / PAGE_SIZE)),
  );

  protected filter(status: EventStatusEnum | null): void {
    this.status.set(status);
    this.page.set(1);
  }
}
