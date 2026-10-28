import { Component, computed, inject, input, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { Router, RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import { eventsCreate } from '../../../core/api/functions';
import { EventWriteRequest } from '../../../core/api/models';
import { AuthService } from '../../../core/auth/auth.service';
import { errorText } from '../../../shared/api-errors';
import { EventTicket, EventTicketData } from '../../../shared/event-ticket/event-ticket';
import { fromLocalInput } from '../../../shared/events';
import { EventForm } from '../event-form/event-form';

type Draft = Partial<{
  title: string;
  location: string;
  start_at: string;
  image_url: string;
  capacity: number;
}>;

/** New events start as drafts; categories are added right after, in the "Entradas" tab. */
@Component({
  selector: 'app-event-create',
  imports: [RouterLink, MatIconModule, EventForm, EventTicket],
  templateUrl: './event-create.html',
  styleUrl: './event-create.scss',
})
export class EventCreate {
  private readonly api = inject(Api);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** `:org` route parameter. */
  readonly org = input.required<string>();

  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly draft = signal<Draft>({});

  /** The card the public will see, built from what is being typed. */
  protected readonly preview = computed<EventTicketData>(() => {
    const draft = this.draft();
    const organization = this.auth
      .user()
      ?.memberships.find((m) => m.organization_slug === this.org());
    let startAt = '';
    try {
      startAt = draft.start_at ? fromLocalInput(draft.start_at) : '';
    } catch {
      // half-typed date: keep the placeholder
    }
    return {
      title: draft.title ?? '',
      location: draft.location ?? '',
      start_at: startAt,
      image_url: /^https?:\/\/\S+$/.test(draft.image_url ?? '') ? draft.image_url! : '',
      organization_name: organization?.organization_name ?? '',
      available: Math.max(0, draft.capacity ?? 0),
    };
  });

  protected async create(body: EventWriteRequest): Promise<void> {
    this.saving.set(true);
    this.error.set(null);
    try {
      const event = await this.api.invoke(eventsCreate, { org_slug: this.org(), body });
      await this.router.navigate(['/org', this.org(), 'events', event.id], {
        queryParams: { tab: 'entradas' },
      });
    } catch (error) {
      this.error.set(errorText(error));
    } finally {
      this.saving.set(false);
    }
  }
}
