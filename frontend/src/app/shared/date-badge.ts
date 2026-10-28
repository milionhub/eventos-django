import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';

/** Poster-style date: big day number over the abbreviated month. */
@Component({
  selector: 'app-date-badge',
  imports: [DatePipe],
  template: `
    <time [attr.datetime]="date()">
      <span class="day">{{ date() | date: 'd' }}</span>
      <span class="month">{{ date() | date: 'MMM' }}</span>
    </time>
  `,
  styles: `
    time {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 56px;
      line-height: 1;
    }

    .day {
      font-family: var(--app-font-display);
      font-size: 2rem;
      font-weight: 800;
      letter-spacing: -0.04em;
    }

    .month {
      margin-top: 4px;
      color: var(--app-accent);
      font: var(--mat-sys-label-medium);
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
  `,
})
export class DateBadge {
  readonly date = input.required<string>();
}
