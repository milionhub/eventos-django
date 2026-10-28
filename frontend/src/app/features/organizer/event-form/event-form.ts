import { Component, computed, effect, inject, input, output, viewChild } from '@angular/core';
import { outputFromObservable, toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DATE_LOCALE, provideNativeDateAdapter } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTimepickerModule } from '@angular/material/timepicker';
import { RouterLink } from '@angular/router';

import { EventDetail, EventWriteRequest } from '../../../core/api/models';
import { ImageChange, ImagePicker } from '../../../shared/image-picker/image-picker';

/** What the form hands over on save: the event data and what to do with its image. */
export interface EventFormValue {
  data: EventWriteRequest;
  image: ImageChange;
}

const HOUR = 3600 * 1000;

/** The day of `date` at the time of day of `time`; null until both are chosen. */
function combine(date: Date | null | undefined, time: Date | null | undefined): Date | null {
  if (!date || !time) return null;
  return new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
    time.getHours(),
    time.getMinutes(),
  );
}

interface DateTimeParts {
  startDate?: Date | null;
  startTime?: Date | null;
  endDate?: Date | null;
  endTime?: Date | null;
}

/** UX only: the backend checks the same rule (InvalidDates). */
function endAfterStart(group: AbstractControl): ValidationErrors | null {
  const v = group.value as DateTimeParts;
  const start = combine(v.startDate, v.startTime);
  const end = combine(v.endDate, v.endTime);
  return start && end && end <= start ? { endBeforeStart: true } : null;
}

/** "3 h 30 min" between two moments, or null if they are not set or not in order. */
function duration(start: Date | null | undefined, end: Date | null | undefined): string | null {
  if (!start || !end) return null;
  const minutes = (end.getTime() - start.getTime()) / 60000;
  if (!(minutes > 0)) return null;
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const rest = Math.round(minutes % 60);
  return [days && `${days} d`, hours && `${hours} h`, rest && `${rest} min`]
    .filter(Boolean)
    .join(' ');
}

function startOfToday(): Date {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

/** The "Datos" of an event, used to create one and to edit it. */
@Component({
  selector: 'app-event-form',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTimepickerModule,
    ImagePicker,
  ],
  // Dates in Spanish, weeks starting on Monday. Kept here so the initial bundle stays lean.
  providers: [provideNativeDateAdapter(), { provide: MAT_DATE_LOCALE, useValue: 'es-ES' }],
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
  readonly save = output<EventFormValue>();
  /** URL of the image being shown, for live previews next to the form. */
  readonly imagePreview = output<string>();

  private readonly picker = viewChild.required(ImagePicker);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly today = startOfToday();
  protected readonly quickDurations = [1, 2, 3, 4];

  protected readonly form = this.fb.group(
    {
      title: ['', [Validators.required, Validators.maxLength(200)]],
      location: ['', [Validators.required, Validators.maxLength(255)]],
      description: [''],
      // Day and time are separate controls: picking a day in the calendar must never
      // reset the time already chosen. They are combined only to validate and save.
      startDate: this.fb.control<Date | null>(null, Validators.required),
      startTime: this.fb.control<Date | null>(null, Validators.required),
      endDate: this.fb.control<Date | null>(null, Validators.required),
      endTime: this.fb.control<Date | null>(null, Validators.required),
      capacity: this.fb.control(100, [Validators.required, Validators.min(1)]),
    },
    { validators: endAfterStart },
  );

  /** Every change, as typed, with the start as an instant: feeds the live preview. */
  readonly changes = outputFromObservable(
    this.form.valueChanges.pipe(
      map((v) => ({
        title: v.title ?? '',
        location: v.location ?? '',
        capacity: v.capacity ?? 0,
        start_at: combine(v.startDate, v.startTime)?.toISOString() ?? '',
      })),
    ),
  );

  private readonly value = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });
  protected readonly start = computed(() =>
    combine(this.value().startDate, this.value().startTime),
  );
  protected readonly duration = computed(() =>
    duration(this.start(), combine(this.value().endDate, this.value().endTime)),
  );

  constructor() {
    effect(() => {
      const event = this.event();
      if (event) {
        const start = new Date(event.start_at);
        const end = new Date(event.end_at);
        this.form.reset({
          title: event.title,
          location: event.location,
          description: event.description,
          startDate: start,
          startTime: start,
          endDate: end,
          endTime: end,
          capacity: event.capacity,
        });
      }
    });
    effect(() => (this.readonly() ? this.form.disable() : this.form.enable()));
  }

  /** "+2 h": the end, counted from the start (keeps the same day if possible). */
  protected endAfter(hours: number): void {
    const start = this.start();
    if (!start) return;
    const end = new Date(start.getTime() + hours * HOUR);
    this.form.patchValue({ endDate: end, endTime: end });
    this.form.markAsDirty();
  }

  protected imageChanged(url: string): void {
    this.imagePreview.emit(url);
    if (this.picker().hasChanges()) this.form.markAsDirty();
  }

  /** After a successful save the picked image becomes the current one. */
  saved(): void {
    this.picker().reset();
    this.form.markAsPristine();
  }

  protected async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { startDate, startTime, endDate, endTime, ...rest } = this.form.getRawValue();
    this.save.emit({
      data: {
        ...rest,
        start_at: combine(startDate, startTime)!.toISOString(),
        end_at: combine(endDate, endTime)!.toISOString(),
      },
      image: await this.picker().change(),
    });
  }
}
