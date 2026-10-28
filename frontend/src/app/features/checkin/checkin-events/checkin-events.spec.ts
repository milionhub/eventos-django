import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { CheckinEvent } from '../../../core/api/models';
import { CheckinEvents } from './checkin-events';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));

const event = (id: number, is_open: boolean): CheckinEvent => ({
  id,
  slug: `e${id}`,
  title: `Evento ${id}`,
  location: 'Barcelona',
  image_url: '',
  start_at: '2026-11-18T19:00:00Z',
  end_at: '2026-11-18T22:00:00Z',
  organization_name: 'Sala Apolo',
  opens_at: '2026-11-18T16:00:00Z',
  is_open,
});

describe('CheckinEvents', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CheckinEvents],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function render(events: CheckinEvent[]): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(CheckinEvents);
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne('/api/v1/checkin/events/').flush(events);
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('lists my events, telling apart open doors from upcoming ones', async () => {
    const element = await render([event(1, true), event(2, false)]);

    const rows = element.querySelectorAll('a.row');
    expect(rows[0].getAttribute('href')).toBe('/checkin/1');
    expect(rows[0].textContent).toContain('Puerta abierta');
    expect(rows[1].textContent).toContain('Abre');
  });

  it('explains why the list can be empty', async () => {
    const element = await render([]);

    expect(element.textContent).toContain('No tienes eventos para validar');
  });
});
