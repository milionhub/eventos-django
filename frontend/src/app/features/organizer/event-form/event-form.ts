import { Component, computed, effect, inject, input, output } from '@angular/core';
import { outputFromObservable, toSignal } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { EventDetail, EventWriteRequest } from '../../../core/api/models';
import { fromLocalInput, toLocalInput } from '../../../shared/events';

/** UX only: the backend checks the same rule (InvalidDates). */
function endAfterStart(group: AbstractControl): ValidationErrors | null {
  const { start_at, end_at } = group.value as { start_at: string; end_at: string };
  return start_at && end_at && end_at <= start_at ? { endBeforeStart: true } : null;
}

const IMAGE_URL = /^https?:\/\/\S+$/;

/** "3 h 30 min" between two datetime-local values, or null if they are not valid. */
function duration(start: string, end: string): string | null {
  const minutes = (new Date(end).getTime() - new Date(start).getTime()) / 60000;
  if (!start || !end || !(minutes > 0)) return null;
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const rest = Math.round(minutes % 60);
  return [days && `${days} d`, hours && `${hours} h`, rest && `${rest} min`]
    .filter(Boolean)
    .join(' ');
}

/** The "Datos" of an event, used to create one and to edit it. */
@Component({
  selector: 'app-event-form',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './event-form.html',
  styleUrl: './event-form.scss',
})
export class EventForm {
  /** Event to edit; null to create a new one. */
  readonly event = input<EventDetail | null>(null);
  readonly busy = input(false);
  readonly readonly = input(false);
  readonly submitLabel = input('Guardar cambios');
  /** Where "Cancelar" goes; no button when unset. */
  readonly cancelLink = input<unknown[] | null>(null);
  readonly save = output<EventWriteRequest>();

  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly form = this.fb.group(
    {
      title: ['', [Validators.required, Validators.maxLength(200)]],
      location: ['', [Validators.required, Validators.maxLength(255)]],
      description: [''],
      image_url: ['', Validators.pattern(IMAGE_URL)],
      start_at: ['', Validators.required],
      end_at: ['', Validators.required],
      capacity: this.fb.control(100, [Validators.required, Validators.min(1)]),
    },
    { validators: endAfterStart },
  );

  /** Every change, as typed: feeds the live preview next to the form. */
  readonly changes = outputFromObservable(this.form.valueChanges);

  private readonly value = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });
  protected readonly duration = computed(() =>
    duration(this.value().start_at ?? '', this.value().end_at ?? ''),
  );
  protected readonly imagePreview = computed(() => {
    const url = this.value().image_url ?? '';
    return IMAGE_URL.test(url) ? url : null;
  });

  constructor() {
    effect(() => {
      const event = this.event();
      if (event) {
        this.form.reset({
          title: event.title,
          location: event.location,
          description: event.description,
          image_url: event.image_url,
          start_at: toLocalInput(event.start_at),
          end_at: toLocalInput(event.end_at),
          capacity: event.capacity,
        });
      }
    });
    effect(() => (this.readonly() ? this.form.disable() : this.form.enable()));
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.save.emit({
      ...value,
      start_at: fromLocalInput(value.start_at),
      end_at: fromLocalInput(value.end_at),
    });
  }
}
