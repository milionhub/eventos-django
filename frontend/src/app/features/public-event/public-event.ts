import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input, linkedSignal, resource } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { Api } from '../../core/api/api';
import { publicEventsRetrieve } from '../../core/api/functions';
import { AuthService } from '../../core/auth/auth.service';
import { CapitalizePipe } from '../../shared/capitalize.pipe';

/** Public page of one event (R2, steps 2–3). Booking itself arrives in Phase 3. */
@Component({
  selector: 'app-public-event',
  imports: [
    CapitalizePipe,
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './public-event.html',
  styleUrl: './public-event.scss',
})
export class PublicEvent {
  private readonly api = inject(Api);
  protected readonly auth = inject(AuthService);

  /** `:slug` route parameter. */
  readonly slug = input.required<string>();

  protected readonly event = resource({
    params: () => ({ slug: this.slug() }),
    loader: ({ params }) => this.api.invoke(publicEventsRetrieve, params),
  });
  protected readonly notFound = computed(() => {
    const error = this.event.error();
    return error instanceof HttpErrorResponse && error.status === 404;
  });

  /** Selected category: the first one with seats left, until the user picks another. */
  protected readonly selected = linkedSignal(
    () => this.event.value()?.ticket_types.find((t) => !t.sold_out)?.id ?? null,
  );
  protected readonly soldOut = computed(() => this.event.value()?.available === 0);
  protected readonly returnUrl = computed(() => `/events/${this.slug()}`);
}
