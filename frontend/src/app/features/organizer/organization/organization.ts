import { Component, inject, input, resource } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import { organizationsRetrieve } from '../../../core/api/functions';
import { ROLE_LABELS } from '../../../shared/roles';

/** Landing page of one organization. Grows into the dashboard in Phase 5. */
@Component({
  selector: 'app-organization',
  imports: [RouterLink, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './organization.html',
  styleUrl: './organization.scss',
})
export class Organization {
  private readonly api = inject(Api);

  /** `:org` route parameter. */
  readonly org = input.required<string>();

  protected readonly roleLabels = ROLE_LABELS;
  protected readonly details = resource({
    params: () => ({ org_slug: this.org() }),
    loader: ({ params }) => this.api.invoke(organizationsRetrieve, params),
  });
}
