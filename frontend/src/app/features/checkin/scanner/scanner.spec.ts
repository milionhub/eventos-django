import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { ZXingScannerModule } from '@zxing/ngx-scanner';
import { vi } from 'vitest';

import { CheckinEvent, ScanResult } from '../../../core/api/models';
import { Scanner } from './scanner';

/** Stands in for the camera component: jsdom has no camera. */
// eslint-disable-next-line @angular-eslint/component-selector -- must match the real one
@Component({ selector: 'zxing-scanner', template: '' })
class FakeCamera {
  @Input() formats: unknown;
  @Input() device: unknown;
  @Input() autofocusEnabled = false;
  @Input() previewFitMode = '';
  @Output() scanSuccess = new EventEmitter<string>();
  @Output() permissionResponse = new EventEmitter<boolean>();
  @Output() camerasFound = new EventEmitter<MediaDeviceInfo[]>();
  @Output() camerasNotFound = new EventEmitter<void>();
}

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const SCAN = '/api/v1/checkin/events/7/scan/';
const ACTIVITY = '/api/v1/checkin/events/7/activity/';

const EVENT: CheckinEvent = {
  id: 7,
  slug: 'jazz',
  title: 'Noche de Jazz',
  location: 'Barcelona',
  image_url: '',
  start_at: '2026-11-18T19:00:00Z',
  end_at: '2026-11-18T22:30:00Z',
  organization_name: 'Sala Apolo',
  opens_at: '2026-11-18T16:00:00Z',
  is_open: true,
};

const valid: ScanResult = {
  result: 'VALID',
  checked_at: '2026-11-18T19:05:00Z',
  ticket: { id: 't1', ticket_type: 'VIP', holder_name: 'Laura Gómez', checked_in_at: null },
};

describe('Scanner', () => {
  let fixture: ComponentFixture<Scanner>;
  let http: HttpTestingController;
  const vibrate = vi.fn();

  beforeEach(async () => {
    vibrate.mockClear();
    Object.assign(navigator, { vibrate });
    await TestBed.configureTestingModule({
      imports: [Scanner],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    })
      .overrideComponent(Scanner, {
        remove: { imports: [ZXingScannerModule] },
        add: { imports: [FakeCamera] },
      })
      .compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const element = () => fixture.nativeElement as HTMLElement;
  const camera = () =>
    fixture.debugElement.query(By.directive(FakeCamera)).componentInstance as FakeCamera;

  async function settle(): Promise<void> {
    await flushMicrotasks();
    fixture.detectChanges();
    await flushMicrotasks();
  }

  async function render(event: CheckinEvent = EVENT): Promise<void> {
    fixture = TestBed.createComponent(Scanner);
    fixture.componentRef.setInput('id', '7');
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne('/api/v1/checkin/events/').flush([event]);
    http.expectOne(ACTIVITY).flush({ stats: { validated: 3, expected: 120 }, logs: [] });
    await settle();
  }

  async function scanned(code: string, answer: ScanResult | null = valid): Promise<void> {
    camera().scanSuccess.emit(code);
    await flushMicrotasks();
    if (answer) {
      const req = http.expectOne(SCAN);
      expect(req.request.body).toEqual({ token: code });
      req.flush(answer);
      await settle();
      http.expectOne(ACTIVITY).flush({ stats: { validated: 4, expected: 120 }, logs: [] });
      await settle();
    }
  }

  it('shows how many people are in', async () => {
    await render();

    expect(element().querySelector('.count')?.textContent).toContain('3');
    expect(element().querySelector('.count')?.textContent).toContain('120');
  });

  it('shows a valid ticket full screen, with the holder, and buzzes once', async () => {
    await render();

    await scanned('token-1');

    const result = element().querySelector('.result')!;
    expect(result.getAttribute('data-tone')).toBe('ok');
    expect(result.textContent).toContain('Válida');
    expect(result.textContent).toContain('Laura Gómez');
    expect(result.textContent).toContain('VIP');
    expect(vibrate).toHaveBeenCalledWith([80]);
  });

  it('says when an already used ticket came in', async () => {
    await render();

    await scanned('token-1', {
      ...valid,
      result: 'ALREADY_USED',
      ticket: { ...valid.ticket!, checked_in_at: '2026-11-18T19:01:00Z' },
    });

    const result = element().querySelector('.result')!;
    expect(result.getAttribute('data-tone')).toBe('warn');
    expect(result.textContent).toContain('Entró a las');
  });

  it('ignores the same code read again a moment later', async () => {
    await render();
    await scanned('token-1');
    element().querySelector<HTMLButtonElement>('.result')!.click();
    await settle();

    camera().scanSuccess.emit('token-1');
    await flushMicrotasks();

    http.expectNone(SCAN);
  });

  it('ignores reads while a result is on screen', async () => {
    await render();
    await scanned('token-1');

    camera().scanSuccess.emit('token-2');
    await flushMicrotasks();

    http.expectNone(SCAN);
  });

  it('shows UNAUTHORIZED, which comes as a 403', async () => {
    await render();
    camera().scanSuccess.emit('token-1');
    await flushMicrotasks();

    http
      .expectOne(SCAN)
      .flush({ ...valid, result: 'UNAUTHORIZED', ticket: null }, { status: 403, statusText: '' });
    await settle();
    http.expectOne(ACTIVITY).flush({ stats: { validated: 3, expected: 120 }, logs: [] });
    await settle();

    expect(element().querySelector('.result')?.textContent).toContain('No puedes validar aquí');
  });

  it('never shows a result when the server could not be reached', async () => {
    await render();
    camera().scanSuccess.emit('token-1');
    await flushMicrotasks();

    http.expectOne(SCAN).error(new ProgressEvent('error'));
    await settle();
    http.expectOne(ACTIVITY).flush({ stats: { validated: 3, expected: 120 }, logs: [] });
    await settle();

    expect(element().querySelector('.result')).toBeNull();
    expect(element().querySelector('[role="alert"]')?.textContent).toContain('no se ha validado');
  });

  it('validates a code typed by hand', async () => {
    await render();
    const input = element().querySelector<HTMLInputElement>('#manual-code')!;
    input.value = '  token-9 ';
    input.dispatchEvent(new Event('input'));
    element().querySelector<HTMLFormElement>('form.manual')!.dispatchEvent(new Event('submit'));
    await flushMicrotasks();

    expect(http.expectOne(SCAN).request.body).toEqual({ token: 'token-9' });
  });

  it('explains a denied camera and keeps manual entry', async () => {
    await render();

    camera().permissionResponse.emit(false);
    await settle();

    expect(element().textContent).toContain('Sin permiso para usar la cámara');
    expect(element().querySelector('#manual-code')).toBeTruthy();
  });

  it('warns when the door is not open yet', async () => {
    await render({ ...EVENT, is_open: false });

    expect(element().textContent).toContain('La puerta abre');
  });
});
