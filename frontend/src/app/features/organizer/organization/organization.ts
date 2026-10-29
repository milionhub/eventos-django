import { DatePipe } from '@angular/common';
import { Component, inject, input, resource } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import { organizationsRetrieve, organizationStats } from '../../../core/api/functions';
import { CapitalizePipe } from '../../../shared/capitalize.pipe';
import { EventThumb } from '../../../shared/event-thumb';
import { Meter } from '../../../shared/meter';
import { ROLE_LABELS } from '../../../shared/roles';
import { StatTile } from '../../../shared/stat-tile';
import { percent } from '../../../shared/stats';

/** One organization: the dashboard for organizers (R5), shortcuts for everyone. */
@Component({
  selector: 'app-organization',
  imports: [
    CapitalizePipe,
    DatePipe,
    EventThumb,
    Meter,
    RouterLink,
    StatTile,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './organization.html',
  styleUrl: './organization.scss',
})
export class Organization {
  private readonly api = inject(Api);

  /** `:org` route parameter. */
  readonly org = input.required<string>();

  protected readonly roleLabels = ROLE_LABELS;
  protected readonly percent = percent;
  protected readonly details = resource({
    params: () => ({ org_slug: this.org() }),
    loader: ({ params }) => this.api.invoke(organizationsRetrieve, params),
  });

  // Stats are for OWNER and MANAGER only (§4): STAFF never asks (the API would say 403).
  protected readonly stats = resource({
    params: () => {
      const role = this.details.value()?.role;
      return role === 'OWNER' || role === 'MANAGER' ? { org_slug: this.org() } : undefined;
    },
    loader: ({ params }) => this.api.invoke(organizationStats, params),
  });
}
