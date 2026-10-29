import { Component, computed, input } from '@angular/core';

/**
 * A thin bar for a ratio against a limit (seats taken, people in). The track is a light
 * step of the same accent, so the whole bar reads as one quantity. The figures always
 * go next to it as text: the bar alone never carries the number.
 */
@Component({
  selector: 'app-meter',
  template: `
    <div
      class="track"
      role="meter"
      aria-valuemin="0"
      [attr.aria-valuemax]="max()"
      [attr.aria-valuenow]="value()"
      [attr.aria-valuetext]="value() + ' de ' + max()"
      [attr.aria-label]="label()"
    >
      <span class="fill" [style.width.%]="width()"></span>
    </div>
  `,
  styles: `
    :host {
      display: block;
    }

    .track {
      height: 8px;
      overflow: hidden;
      border-radius: 4px;
      background: color-mix(in srgb, var(--app-accent) 16%, transparent);
    }

    .fill {
      display: block;
      height: 100%;
      border-radius: 4px;
      background: var(--app-accent);
    }

    // Windows high contrast: keep the bar visible without background colors.
    @media (forced-colors: active) {
      .track {
        border: 1px solid CanvasText;
      }

      .fill {
        background: Highlight;
      }
    }
  `,
})
export class Meter {
  readonly value = input.required<number>();
  readonly max = input.required<number>();
  /** What is being measured, for screen readers ("Plazas reservadas"). */
  readonly label = input.required<string>();

  /** Never wider than the track; a small non-zero value still shows a sliver. */
  protected readonly width = computed(() => {
    const max = this.max();
    if (max <= 0 || this.value() <= 0) return 0;
    return Math.min(100, Math.max(2, (this.value() / max) * 100));
  });
}
