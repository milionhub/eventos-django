import { Component, computed, inject, input, linkedSignal, resource } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterLink } from '@angular/router';

import { Api } from '../../core/api/api';
import { publicEventsList } from '../../core/api/functions';
import { EventTicket } from '../../shared/event-ticket/event-ticket';

/** Must match the backend's PAGE_SIZE. */
const PAGE_SIZE = 20;

/** Public landing page: upcoming published events, searchable (R2, step 1). */
@Component({
  selector: 'app-home',
  imports: [
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    EventTicket,
  ],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home {
  private readonly api = inject(Api);
  private readonly router = inject(Router);

  /** `?q=` query parameter: the search lives in the URL so it can be shared. */
  readonly q = input<string>();

  /** What the user is typing; reset whenever the URL changes. */
  protected readonly search = linkedSignal(() => this.q() ?? '');
  /** Back to the first page on every new search. */
  protected readonly page = linkedSignal({ source: this.q, computation: () => 1 });

  protected readonly events = resource({
    params: () => ({ q: this.q() || undefined, page: this.page() }),
    loader: ({ params }) => this.api.invoke(publicEventsList, params),
  });
  protected readonly pages = computed(() =>
    Math.max(1, Math.ceil((this.events.value()?.count ?? 0) / PAGE_SIZE)),
  );

  protected submit(): void {
    const q = this.search().trim();
    void this.router.navigate([], { queryParams: { q: q || null } });
  }
}
