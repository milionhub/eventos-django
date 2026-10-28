import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

import { CapitalizePipe } from '../capitalize.pipe';

/** What the card needs: a public event, or a draft being typed in the event form. */
export interface EventTicketData {
  title: string;
  location: string;
  start_at: string;
  image_url: string;
  organization_name: string;
  available: number;
  /** Links to the public page when set; previews have none. */
  slug?: string;
}

/** An event as a perforated ticket: poster, details and a stub with the seats left. */
@Component({
  selector: 'app-event-ticket',
  imports: [CapitalizePipe, DatePipe, NgTemplateOutlet, RouterLink, MatIconModule],
  templateUrl: './event-ticket.html',
  styleUrl: './event-ticket.scss',
})
export class EventTicket {
  readonly event = input.required<EventTicketData>();
}
