import { DatePipe } from '@angular/common';
import { Component, inject, resource } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import { checkinEventsList } from '../../../core/api/functions';
import { CapitalizePipe } from '../../../shared/capitalize.pipe';
import { EventThumb } from '../../../shared/event-thumb';

/** R4, steps 1–2: the events where I can validate tickets, and when their door opens. */
@Component({
  selector: 'app-checkin-events',
  imports: [
    CapitalizePipe,
    DatePipe,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    EventThumb,
  ],
  templateUrl: './checkin-events.html',
  styleUrl: './checkin-events.scss',
})
export class CheckinEvents {
  private readonly api = inject(Api);

  protected readonly events = resource({ loader: () => this.api.invoke(checkinEventsList) });
}
