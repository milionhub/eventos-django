import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, input, resource, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import { myTicketsQr, myTicketsRetrieve, reservationsCancel } from '../../../core/api/functions';
import { AuthService } from '../../../core/auth/auth.service';
import { errorText } from '../../../shared/api-errors';
import { CapitalizePipe } from '../../../shared/capitalize.pipe';
import { TICKET_STATUS_LABELS } from '../../../shared/tickets';

/** One ticket with its QR, as it is shown at the door (R2 step 5, R3). */
@Component({
  selector: 'app-ticket',
  imports: [
    CapitalizePipe,
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './ticket.html',
  styleUrl: './ticket.scss',
})
export class Ticket {
  private readonly api = inject(Api);
  private readonly auth = inject(AuthService);

  /** Route parameters: `:id`, and `?nueva=1` right after booking. */
  readonly id = input.required<string>();
  readonly nueva = input<string>();

  protected readonly statusLabels = TICKET_STATUS_LABELS;
  protected readonly holder = computed(() => {
    const user = this.auth.user();
    return user ? `${user.first_name} ${user.last_name}`.trim() || user.email : '';
  });

  protected readonly ticket = resource({
    params: () => ({ ticket_id: this.id() }),
    loader: ({ params }) => this.api.invoke(myTicketsRetrieve, params),
  });
  protected readonly notFound = computed(() => {
    const error = this.ticket.error();
    return error instanceof HttpErrorResponse && error.status === 404;
  });

  /**
   * The QR is downloaded with HttpClient, which sends the access token in its header, and
   * shown through a `blob:` URL. An <img src="…/qr.svg"> could not authenticate, and the
   * token must never travel in a URL. Cancelled tickets have no QR to show.
   */
  private readonly qr = resource({
    params: () => {
      const ticket = this.ticket.value();
      return ticket && ticket.status !== 'CANCELLED' ? { ticket_id: ticket.id } : undefined;
    },
    loader: ({ params }) => this.api.invoke(myTicketsQr, params),
  });
  protected readonly qrUrl = signal<string | null>(null);

  protected readonly confirming = signal(false);
  protected readonly cancelling = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    effect((onCleanup) => {
      const svg = this.qr.value();
      if (!svg) {
        this.qrUrl.set(null);
        return;
      }
      const url = URL.createObjectURL(svg);
      this.qrUrl.set(url);
      onCleanup(() => URL.revokeObjectURL(url)); // free it when it changes or we leave
    });
  }

  /** First click asks; the second one cancels (RN-20). */
  protected async cancel(): Promise<void> {
    const ticket = this.ticket.value();
    if (!ticket) return;
    if (!this.confirming()) {
      this.confirming.set(true);
      return;
    }
    this.confirming.set(false);
    this.cancelling.set(true);
    this.error.set(null);
    try {
      await this.api.invoke(reservationsCancel, { reservation_id: ticket.reservation.id });
      this.ticket.reload();
    } catch (error) {
      this.error.set(errorText(error));
    } finally {
      this.cancelling.set(false);
    }
  }
}
