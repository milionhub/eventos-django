import { DatePipe } from '@angular/common';
import {
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  numberAttribute,
  resource,
  signal,
  viewChild,
} from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { Api } from '../../../core/api/api';
import {
  eventsCancel,
  eventsPublish,
  eventsRetrieve,
  eventsImageDestroy,
  eventsImageUpdate,
  eventsUpdate,
  membersList,
  staffCreate,
  staffDestroy,
  staffList,
  ticketTypesCreate,
  ticketTypesDestroy,
  ticketTypesUpdate,
} from '../../../core/api/functions';
import { EventStaff, TicketType } from '../../../core/api/models';
import { errorText } from '../../../shared/api-errors';
import { CapitalizePipe } from '../../../shared/capitalize.pipe';
import { eventStatusLabel } from '../../../shared/events';
import { initials, ROLE_LABELS } from '../../../shared/roles';
import { EventAttendees } from '../event-attendees/event-attendees';
import { EventForm, EventFormValue } from '../event-form/event-form';
import { EventStats } from '../event-stats/event-stats';

const TABS = ['datos', 'entradas', 'staff', 'asistentes', 'stats'];
const STAFF_TAB = 2;

interface Notice {
  kind: 'success' | 'error';
  text: string;
}

/** Manage one event: data, categories, staff, attendees and stats; publish or cancel it. */
@Component({
  selector: 'app-event-manage',
  imports: [
    CapitalizePipe,
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTabsModule,
    EventAttendees,
    EventForm,
    EventStats,
  ],
  templateUrl: './event-manage.html',
  styleUrl: './event-manage.scss',
})
export class EventManage {
  private readonly api = inject(Api);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  /** Route parameters: `:org`, `:id` and `?tab=` (datos | entradas | staff | asistentes | stats). */
  readonly org = input.required<string>();
  readonly id = input.required({ transform: numberAttribute });
  readonly tab = input<string>();

  protected readonly statusLabel = eventStatusLabel;
  protected readonly roleLabels = ROLE_LABELS;
  protected readonly initials = initials;
  protected readonly selectedTab = linkedSignal(() => Math.max(0, TABS.indexOf(this.tab() ?? '')));

  private readonly ids = computed(() => ({ org_slug: this.org(), event_id: this.id() }));

  protected readonly event = resource({
    params: this.ids,
    loader: ({ params }) => this.api.invoke(eventsRetrieve, params),
  });

  // Staff data is only fetched once its tab is opened.
  protected readonly staff = resource({
    params: () => (this.selectedTab() === STAFF_TAB ? this.ids() : undefined),
    loader: ({ params }) => this.api.invoke(staffList, params),
  });
  protected readonly members = resource({
    params: () => (this.selectedTab() === STAFF_TAB ? { org_slug: this.org() } : undefined),
    loader: ({ params }) => this.api.invoke(membersList, params),
  });
  protected readonly candidates = computed(() => {
    const assigned = new Set(this.staff.value()?.map((a) => a.user.id));
    return (this.members.value() ?? []).filter((m) => !assigned.has(m.user.id));
  });

  /** Seats of the event not yet given to any category (RN-13). */
  protected readonly remaining = computed(() => {
    const event = this.event.value();
    return event ? Math.max(0, event.capacity - event.allocated_capacity) : 0;
  });

  protected readonly editable = computed(() => {
    const event = this.event.value();
    return !!event && event.status !== 'CANCELLED' && !event.is_finished;
  });

  private readonly eventForm = viewChild(EventForm);

  protected readonly notice = signal<Notice | null>(null);
  /** Key of the action in progress, to disable just its button. */
  protected readonly busy = signal<string | null>(null);
  /** Key of the destructive action waiting for a second click. */
  protected readonly confirming = signal<string | null>(null);

  protected readonly ticketForm = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(80)]],
    capacity: this.fb.control(50, [Validators.required, Validators.min(1)]),
    description: ['', Validators.maxLength(255)],
  });
  protected readonly editing = signal<number | null>(null);
  protected readonly editForm = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(80)]],
    capacity: this.fb.control(1, [Validators.required, Validators.min(1)]),
  });
  protected readonly staffChoice = this.fb.control<number | null>(null, Validators.required);

  constructor() {
    // UX only: the backend enforces RN-13 again.
    effect(() => {
      const capacity = this.ticketForm.controls.capacity;
      capacity.setValidators([
        Validators.required,
        Validators.min(1),
        Validators.max(this.remaining()),
      ]);
      capacity.updateValueAndValidity({ emitEvent: false });
    });
  }

  /** The open tab goes into the URL, so a reload or a shared link opens the same one. */
  protected selectTab(index: number): void {
    this.selectedTab.set(index);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab: index ? TABS[index] : null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  // --- event ---------------------------------------------------------------------------

  /** The event data first, then its image if it changed (separate multipart endpoint). */
  protected async saveData({ data, image }: EventFormValue): Promise<boolean> {
    const ok = await this.run('data', 'Cambios guardados.', async () => {
      await this.api.invoke(eventsUpdate, { ...this.ids(), body: data });
      if (image.kind === 'set') {
        await this.api.invoke(eventsImageUpdate, { ...this.ids(), body: { image: image.blob } });
      } else if (image.kind === 'remove') {
        await this.api.invoke(eventsImageDestroy, this.ids());
      }
    });
    if (ok) this.eventForm()?.saved();
    return ok;
  }

  protected publish(): Promise<boolean> {
    return this.run('publish', 'Evento publicado: ya aparece en la página pública.', () =>
      this.api.invoke(eventsPublish, this.ids()),
    );
  }

  protected cancel(): Promise<boolean> {
    if (!this.confirm('cancel')) return Promise.resolve(false);
    return this.run('cancel', 'Evento cancelado.', () => this.api.invoke(eventsCancel, this.ids()));
  }

  // --- ticket types ------------------------------------------------------------------------

  protected async addTicketType(): Promise<void> {
    if (this.ticketForm.invalid) {
      this.ticketForm.markAllAsTouched();
      return;
    }
    const body = this.ticketForm.getRawValue();
    const ok = await this.run('add-ticket', `Categoría "${body.name}" añadida.`, () =>
      this.api.invoke(ticketTypesCreate, { ...this.ids(), body }),
    );
    if (ok) this.ticketForm.reset({ name: '', capacity: 50, description: '' });
  }

  protected useAllRemaining(): void {
    this.ticketForm.controls.capacity.setValue(this.remaining());
  }

  protected startEdit(ticketType: TicketType): void {
    this.editing.set(ticketType.id);
    this.editForm.reset({ name: ticketType.name, capacity: ticketType.capacity });
  }

  protected async saveTicketType(ticketType: TicketType): Promise<void> {
    if (this.editForm.invalid) return;
    const ok = await this.run(`tt-${ticketType.id}`, 'Categoría actualizada.', () =>
      this.api.invoke(ticketTypesUpdate, {
        ...this.ids(),
        ticket_type_id: ticketType.id,
        body: this.editForm.getRawValue(),
      }),
    );
    if (ok) this.editing.set(null);
  }

  protected deleteTicketType(ticketType: TicketType): Promise<boolean> {
    const key = `tt-${ticketType.id}`;
    if (!this.confirm(key)) return Promise.resolve(false);
    return this.run(key, `Categoría "${ticketType.name}" eliminada.`, () =>
      this.api.invoke(ticketTypesDestroy, { ...this.ids(), ticket_type_id: ticketType.id }),
    );
  }

  // --- staff ---------------------------------------------------------------------------------

  protected async assign(): Promise<void> {
    const user = this.staffChoice.value;
    if (user === null) return;
    const ok = await this.run('assign', 'Persona asignada al evento.', () =>
      this.api.invoke(staffCreate, { ...this.ids(), body: { user } }),
    );
    if (ok) this.staffChoice.reset(null);
  }

  protected unassign(assignment: EventStaff): Promise<boolean> {
    const key = `staff-${assignment.id}`;
    if (!this.confirm(key)) return Promise.resolve(false);
    return this.run(key, 'Asignación retirada.', () =>
      this.api.invoke(staffDestroy, { ...this.ids(), assignment_id: assignment.id }),
    );
  }

  // --- helpers ---------------------------------------------------------------------------

  /** Destructive actions need a second click on the same button. */
  private confirm(key: string): boolean {
    if (this.confirming() !== key) {
      this.confirming.set(key);
      return false;
    }
    this.confirming.set(null);
    return true;
  }

  /** Runs one action, shows the outcome and refreshes what may have changed. */
  private async run(key: string, success: string, action: () => Promise<unknown>) {
    this.busy.set(key);
    this.notice.set(null);
    try {
      await action();
      this.notice.set({ kind: 'success', text: success });
      this.event.reload(); // status, allocated capacity and publish blockers
      if (this.selectedTab() === STAFF_TAB) this.staff.reload();
      return true;
    } catch (error) {
      this.notice.set({ kind: 'error', text: errorText(error) });
      return false;
    } finally {
      this.busy.set(null);
    }
  }
}
