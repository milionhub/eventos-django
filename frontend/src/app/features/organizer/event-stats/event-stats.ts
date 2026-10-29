import { Component, computed, inject, input, resource } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { Api } from '../../../core/api/api';
import { eventStats } from '../../../core/api/functions';
import { ScanResultEnum } from '../../../core/api/models';
import { Meter } from '../../../shared/meter';
import { SCAN_RESULTS } from '../../../shared/scan-results';
import { StatTile } from '../../../shared/stat-tile';
import { percent } from '../../../shared/stats';

/** Most common results first: how the door is going at a glance. */
const RESULT_ORDER: ScanResultEnum[] = [
  'VALID',
  'ALREADY_USED',
  'NOT_FOUND',
  'WRONG_EVENT',
  'CANCELLED',
  'EVENT_NOT_ACTIVE',
  'UNAUTHORIZED',
];

/** The "Stats" tab of an event: occupancy per category and every check-in attempt (R5). */
@Component({
  selector: 'app-event-stats',
  imports: [Meter, StatTile, MatButtonModule, MatIconModule, MatProgressSpinnerModule],
  templateUrl: './event-stats.html',
  styleUrl: './event-stats.scss',
})
export class EventStats {
  private readonly api = inject(Api);

  readonly org = input.required<string>();
  readonly eventId = input.required<number>();

  protected readonly percent = percent;
  protected readonly results = SCAN_RESULTS;
  protected readonly stats = resource({
    params: () => ({ org_slug: this.org(), event_id: this.eventId() }),
    loader: ({ params }) => this.api.invoke(eventStats, params),
  });

  /** Only the results that happened, with their count. */
  protected readonly attempts = computed(() => {
    const scans = this.stats.value()?.scans;
    if (!scans) return [];
    return RESULT_ORDER.filter((result) => scans[result] > 0).map((result) => ({
      result,
      count: scans[result],
    }));
  });
  protected readonly totalAttempts = computed(() =>
    this.attempts().reduce((sum, a) => sum + a.count, 0),
  );
}
