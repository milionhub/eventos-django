import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  numberAttribute,
  resource,
  signal,
} from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { BarcodeFormat } from '@zxing/library';
import { ZXingScannerModule } from '@zxing/ngx-scanner';

import { Api } from '../../../core/api/api';
import { checkinActivity, checkinEventsList, checkinScan } from '../../../core/api/functions';
import { ScanResult } from '../../../core/api/models';
import { SCAN_RESULTS, ScanResultView, VIBRATION } from '../../../shared/scan-results';

/** The camera sees the same QR many times per second: ignore repeats for this long. */
const SAME_CODE_COOLDOWN_MS = 4000;
/** How long a result stays on screen before scanning again. */
const SHOW_MS = { ok: 2000, warn: 3500, error: 3500 } as const;

type CameraState = 'starting' | 'ready' | 'denied' | 'none';

interface Shown {
  view: ScanResultView;
  data: ScanResult;
}

/** R4, steps 3–5: scan QR codes at the door and see a big, clear result. */
@Component({
  selector: 'app-scanner',
  imports: [
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    ZXingScannerModule,
  ],
  templateUrl: './scanner.html',
  styleUrl: './scanner.scss',
})
export class Scanner {
  private readonly api = inject(Api);

  /** `:id` route parameter. */
  readonly id = input.required({ transform: numberAttribute });

  protected readonly formats = [BarcodeFormat.QR_CODE];
  protected readonly results = SCAN_RESULTS;

  private readonly events = resource({ loader: () => this.api.invoke(checkinEventsList) });
  protected readonly event = computed(() => this.events.value()?.find((e) => e.id === this.id()));
  protected readonly activity = resource({
    params: () => ({ event_id: this.id() }),
    loader: ({ params }) => this.api.invoke(checkinActivity, params),
  });

  protected readonly shown = signal<Shown | null>(null);
  protected readonly busy = signal(false);
  protected readonly problem = signal<string | null>(null);
  protected readonly camera = signal<CameraState>('starting');
  protected readonly devices = signal<MediaDeviceInfo[]>([]);
  protected readonly device = signal<MediaDeviceInfo | undefined>(undefined);
  protected readonly manual = inject(NonNullableFormBuilder).control('');

  private lastCode = '';
  private lastCodeAt = 0;
  private hideTimer?: ReturnType<typeof setTimeout>;

  constructor() {
    inject(DestroyRef).onDestroy(() => clearTimeout(this.hideTimer));
  }

  /** From the camera. Ignored while a result is on screen or for an immediate repeat. */
  protected onScan(code: string): void {
    const now = Date.now();
    if (this.shown() || this.busy()) return;
    if (code === this.lastCode && now - this.lastCodeAt < SAME_CODE_COOLDOWN_MS) return;
    this.lastCode = code;
    this.lastCodeAt = now;
    void this.validate(code);
  }

  /** Typed by hand, when there is no camera or the code will not read. */
  protected submitManual(event: Event): void {
    event.preventDefault();
    const code = this.manual.value.trim();
    if (!code) return;
    this.manual.reset();
    void this.validate(code);
  }

  protected onPermission(granted: boolean): void {
    this.camera.set(granted ? 'ready' : 'denied');
  }

  protected onCameras(devices: MediaDeviceInfo[]): void {
    this.devices.set(devices);
    // Prefer the back camera on phones.
    this.device.set(
      devices.find((d) => /back|rear|trasera|environment/i.test(d.label)) ?? devices[0],
    );
  }

  protected nextCamera(): void {
    const devices = this.devices();
    const index = devices.findIndex((d) => d.deviceId === this.device()?.deviceId);
    this.device.set(devices[(index + 1) % devices.length]);
  }

  protected dismiss(): void {
    clearTimeout(this.hideTimer);
    this.shown.set(null);
  }

  private async validate(token: string): Promise<void> {
    this.busy.set(true);
    this.problem.set(null);
    try {
      this.show(await this.api.invoke(checkinScan, { event_id: this.id(), body: { token } }));
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.status === 403 && error.error?.result) {
        this.show(error.error as ScanResult); // UNAUTHORIZED comes as a 403 with the result
      } else if (error instanceof HttpErrorResponse && error.status === 429) {
        this.problem.set('Demasiados escaneos seguidos. Espera unos segundos.');
      } else {
        this.problem.set('No hay conexión con el servidor. La entrada no se ha validado.');
      }
    } finally {
      this.busy.set(false);
      this.activity.reload();
    }
  }

  private show(data: ScanResult): void {
    const view = SCAN_RESULTS[data.result];
    this.shown.set({ view, data });
    navigator.vibrate?.(VIBRATION[view.tone]);
    clearTimeout(this.hideTimer);
    this.hideTimer = setTimeout(() => this.shown.set(null), SHOW_MS[view.tone]);
  }
}
