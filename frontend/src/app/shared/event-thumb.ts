import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';

/** A small 16:9 poster for lists: the event image (or the brand glow) with the date on it. */
@Component({
  selector: 'app-event-thumb',
  imports: [DatePipe],
  template: `
    <div class="thumb" [style.background-image]="imageUrl() ? 'url(' + imageUrl() + ')' : null">
      <time [attr.datetime]="date()">
        <strong>{{ date() | date: 'd' }}</strong>
        {{ date() | date: 'MMM' }}
      </time>
    </div>
  `,
  styles: `
    :host {
      display: block;
      flex: none;
      width: 128px;
    }

    .thumb {
      position: relative;
      aspect-ratio: 16 / 9;
      overflow: hidden;
      border-radius: 10px;
      background:
        radial-gradient(
          120% 140% at 0% 0%,
          color-mix(in srgb, var(--app-accent) 55%, transparent),
          transparent 60%
        ),
        light-dark(#3a3841, var(--mat-sys-surface-container-highest));
      background-position: center;
      background-size: cover;
    }

    // Darken the bottom-left corner so the date reads on any photo.
    .thumb::after {
      position: absolute;
      inset: 0;
      background: linear-gradient(to top right, rgb(0 0 0 / 55%), transparent 60%);
      content: '';
    }

    time {
      position: absolute;
      left: 10px;
      bottom: 6px;
      z-index: 1;
      display: flex;
      flex-direction: column;
      color: #fff;
      font: var(--mat-sys-label-small);
      letter-spacing: 0.12em;
      line-height: 1.1;
      text-transform: uppercase;

      strong {
        font-family: var(--app-font-display);
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.04em;
      }
    }

    @media (max-width: 480px) {
      :host {
        width: 96px;
      }
    }
  `,
})
export class EventThumb {
  readonly date = input.required<string>();
  readonly imageUrl = input('');
}
