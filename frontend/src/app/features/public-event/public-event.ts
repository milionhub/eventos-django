import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input, linkedSignal, resource, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterLink } from '@angular/router';

import { Api } from '../../core/api/api';
import { publicEventsRetrieve, reservationsCreate } from '../../core/api/functions';
import { AuthService } from '../../core/auth/auth.service';
import { CapitalizePipe } from '../../shared/capitalize.pipe';

/** Public page of one event, where attendees book (R2). */
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
  private readonly router = inject(Router);

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

  protected readonly booking = signal(false);
  protected readonly bookingError = signal<{ text: string; mine?: boolean } | null>(null);

  /** Books the selected category and opens the new ticket (R2, step 4). */
  protected async book(): Promise<void> {
    const ticketType = this.selected();
    if (ticketType === null) return;
    this.booking.set(true);
    this.bookingError.set(null);
    try {
      const reservation = await this.api.invoke(reservationsCreate, {
        body: { ticket_type: ticketType },
      });
      await this.router.navigate(['/me/tickets', reservation.ticket.id], {
        queryParams: { nueva: 1 },
      });
    } catch (error) {
      this.bookingError.set(bookingErrorText(error));
      // Someone may have taken the last seats meanwhile: show the current availability.
      if (error instanceof HttpErrorResponse && error.error?.code === 'sold_out') {
        this.event.reload();
      }
    } finally {
      this.booking.set(false);
    }
  }
}

function bookingErrorText(error: unknown): { text: string; mine?: boolean } {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 429) return { text: 'Demasiados intentos. Espera un minuto.' };
    switch (error.error?.code) {
      case 'already_reserved':
        return { text: 'Ya tienes una entrada para este evento.', mine: true };
      case 'sold_out':
        return { text: 'Se acaban de agotar las plazas de esta categoría.' };
    }
    if (error.error?.detail) return { text: error.error.detail };
  }
  return { text: 'No se ha podido completar la reserva. Inténtalo de nuevo.' };
}
