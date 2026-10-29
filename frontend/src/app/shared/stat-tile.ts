import { Component, input } from '@angular/core';

/** One headline figure: a label, the value and an optional line of context. */
@Component({
  selector: 'app-stat-tile',
  template: `
    <p class="label">{{ label() }}</p>
    <p class="value">{{ value() }}</p>
    @if (detail()) {
      <p class="detail">{{ detail() }}</p>
    }
    <ng-content />
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 16px 20px;
      border-radius: var(--app-radius);
      background: var(--mat-sys-surface-container);
    }

    p {
      margin: 0;
    }

    .label {
      color: var(--mat-sys-on-surface-variant);
      font: var(--mat-sys-label-large);
    }

    // Same sans as the rest of the UI: a figure, not a headline.
    .value {
      font: var(--mat-sys-headline-medium);
      font-weight: 600;
    }

    .detail {
      color: var(--mat-sys-on-surface-variant);
      font: var(--mat-sys-body-small);
    }
  `,
})
export class StatTile {
  readonly label = input.required<string>();
  readonly value = input.required<string | number>();
  readonly detail = input<string>();
}
