import { DatePipe } from '@angular/common';
import {
  Component,
  computed,
  inject,
  input,
  linkedSignal,
  output,
  resource,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { debounceTime, distinctUntilChanged, map } from 'rxjs';

import { Api } from '../../../core/api/api';
import { attendeesCancel, attendeesExport, attendeesList } from '../../../core/api/functions';
import { Attendee, TicketStatusEnum } from '../../../core/api/models';
import { errorText } from '../../../shared/api-errors';
import { TICKET_STATUS_LABELS } from '../../../shared/tickets';

/** The API's page size (architecture.md: page-number pagination, 20 per page). */
const PAGE_SIZE = 20;

interface Notice {
  kind: 'success' | 'error';
  text: string;
}

/** The "Asistentes" tab: search, filter, cancel and export the event's reservations (R5). */
@Component({
  selector: 'app-event-attendees',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
  ],
  templateUrl: './event-attendees.html',
  styleUrl: './event-attendees.scss',
})
export class EventAttendees {
  private readonly api = inject(Api);
  private readonly fb = inject(NonNullableFormBuilder);

  readonly org = input.required<string>();
  readonly eventId = input.required<number>();
  /** For the CSV file name. */
  readonly eventSlug = input.required<string>();
  /** Organizers may cancel until the event ends (RN-21); the backend checks it again. */
  readonly cancellable = input(false);
  /** A reservation was cancelled: the parent refreshes its seat counts. */
  readonly changed = output<void>();

  protected readonly statusLabels = TICKET_STATUS_LABELS;
  protected readonly statuses = Object.keys(TICKET_STATUS_LABELS) as TicketStatusEnum[];

  protected readonly filters = this.fb.group({
    q: '',
    status: this.fb.control<TicketStatusEnum | ''>(''),
  });
  // Wait for a pause in typing before asking the API.
  private readonly q = toSignal(
    this.filters.controls.q.valueChanges.pipe(
      debounceTime(300),
      map((value) => value.trim()),
      distinctUntilChanged(),
    ),
    { initialValue: '' },
  );
  private readonly status = toSignal(this.filters.controls.status.valueChanges, {
    initialValue: '' as const,
  });
  /** Back to the first page whenever the filters change. */
  protected readonly page = linkedSignal({
    source: () => [this.q(), this.status()],
    computation: () => 1,
  });

  private readonly query = computed(() => ({
    org_slug: this.org(),
    event_id: this.eventId(),
    q: this.q() || undefined,
    status: this.status() || undefined,
  }));
  protected readonly attendees = resource({
    params: () => ({ ...this.query(), page: this.page() }),
    loader: ({ params }) => this.api.invoke(attendeesList, params),
  });

  /** "21–40 de 54" */
  protected readonly range = computed(() => {
    const count = this.attendees.value()?.count ?? 0;
    const first = (this.page() - 1) * PAGE_SIZE + 1;
    return { first, last: Math.min(count, first + PAGE_SIZE - 1), count };
  });

  protected readonly notice = signal<Notice | null>(null);
  protected readonly busy = signal<string | null>(null);
  protected readonly confirming = signal<string | null>(null);

  protected displayName(attendee: Attendee): string {
    const { first_name, last_name } = attendee.user;
    return `${first_name} ${last_name}`.trim() || 'Sin nombre';
  }

  protected async cancel(attendee: Attendee): Promise<void> {
    if (this.confirming() !== attendee.id) {
      this.confirming.set(attendee.id); // destructive: a second click confirms
      return;
    }
    this.confirming.set(null);
    this.busy.set(attendee.id);
    this.notice.set(null);
    try {
      await this.api.invoke(attendeesCancel, {
        org_slug: this.org(),
        event_id: this.eventId(),
        reservation_id: attendee.id,
      });
      const text = `Reserva de ${this.displayName(attendee)} cancelada.`;
      this.notice.set({ kind: 'success', text });
      this.attendees.reload();
      this.changed.emit();
    } catch (error) {
      this.notice.set({ kind: 'error', text: errorText(error) });
    } finally {
      this.busy.set(null);
    }
  }

  /**
   * A plain <a href> would not carry the JWT (it travels in a header, not a cookie), so the
   * file is fetched like any other call and handed to the browser as a download.
   */
  protected async export(): Promise<void> {
    this.busy.set('export');
    this.notice.set(null);
    try {
      const csv = await this.api.invoke(attendeesExport, {
        ...this.query(),
        // What the box says now: the debounced value lags 300 ms behind the typing.
        q: this.filters.controls.q.value.trim() || undefined,
        tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      const url = URL.createObjectURL(csv);
      const link = document.createElement('a');
      link.href = url;
      link.download = `asistentes-${this.eventSlug()}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      this.notice.set({ kind: 'error', text: errorText(error) });
    } finally {
      this.busy.set(null);
    }
  }
}
