import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { EventStats as EventStatsModel } from '../../../core/api/models';
import { EventStats } from './event-stats';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));

const NO_SCANS = {
  VALID: 0,
  ALREADY_USED: 0,
  CANCELLED: 0,
  NOT_FOUND: 0,
  WRONG_EVENT: 0,
  EVENT_NOT_ACTIVE: 0,
  UNAUTHORIZED: 0,
};

const STATS: EventStatsModel = {
  seats: 60,
  reserved: 45,
  checked_in: 9,
  cancelled: 3,
  ticket_types: [
    { id: 1, name: 'General', capacity: 50, reserved: 40, checked_in: 8 },
    { id: 2, name: 'VIP', capacity: 10, reserved: 5, checked_in: 1 },
  ],
  scans: { ...NO_SCANS, VALID: 9, ALREADY_USED: 2 },
};

describe('EventStats', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventStats],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function render(stats: EventStatsModel = STATS): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(EventStats);
    fixture.componentRef.setInput('org', 'sala-apolo');
    fixture.componentRef.setInput('eventId', 7);
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne('/api/v1/organizations/sala-apolo/events/7/stats/').flush(stats);
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('shows the headline figures', async () => {
    const tiles = [...(await render()).querySelectorAll('app-stat-tile')].map((t) => t.textContent);

    expect(tiles[0]).toContain('45');
    expect(tiles[0]).toContain('de 60 plazas');
    expect(tiles[1]).toContain('75 %');
    expect(tiles[2]).toContain('20 % de las reservas');
    expect(tiles[3]).toContain('3');
  });

  it('shows each category with its bookings and people in', async () => {
    const rows = (await render()).querySelectorAll('.categories li');

    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain('General');
    expect(rows[0].textContent).toContain('40 / 50');
    expect(rows[0].textContent).toContain('8 / 40');
  });

  it('lists only the scan results that happened, with a label next to the icon', async () => {
    const element = await render();
    const items = [...element.querySelectorAll('.attempts li')].map((li) => li.textContent);

    expect(items).toHaveLength(2);
    expect(items[0]).toContain('Válida');
    expect(items[0]).toContain('9');
    expect(items[1]).toContain('Ya utilizada');
    expect(element.textContent).toContain('11 escaneos en total.');
  });

  it('says so when nobody has scanned yet', async () => {
    const element = await render({ ...STATS, scans: NO_SCANS });

    expect(element.querySelector('.attempts')).toBeNull();
    expect(element.textContent).toContain('Todavía nadie ha escaneado');
  });
});
