import { DatePipe } from '@angular/common';
import { Component, computed, inject, resource } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import { myTicketsList } from '../../../core/api/functions';
import { CapitalizePipe } from '../../../shared/capitalize.pipe';
import { EventThumb } from '../../../shared/event-thumb';
import { isUpcoming, TICKET_STATUS_LABELS } from '../../../shared/tickets';

/** "My tickets" (R2 step 5, R3): upcoming ones first, the rest as history. */
@Component({
  selector: 'app-my-tickets',
  imports: [
    CapitalizePipe,
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    EventThumb,
  ],
  templateUrl: './my-tickets.html',
  styleUrl: './my-tickets.scss',
})
export class MyTickets {
  private readonly api = inject(Api);

  protected readonly statusLabels = TICKET_STATUS_LABELS;
  protected readonly tickets = resource({ loader: () => this.api.invoke(myTicketsList) });

  protected readonly upcoming = computed(() =>
    (this.tickets.value() ?? []).filter((t) => isUpcoming(t)),
  );
  /** Most recent first: what happened last is what people look for. */
  protected readonly history = computed(() =>
    (this.tickets.value() ?? []).filter((t) => !isUpcoming(t)).reverse(),
  );
}
