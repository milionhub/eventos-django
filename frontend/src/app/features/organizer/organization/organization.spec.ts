import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { OrganizationStats, RoleEnum } from '../../../core/api/models';
import { Organization } from './organization';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));

const STATS: OrganizationStats = {
  active_events: 2,
  seats: 200,
  reserved: 150,
  checked_in: 30,
  upcoming: [
    {
      id: 7,
      slug: 'noche-de-jazz',
      title: 'Noche de Jazz',
      image_url: '',
      start_at: '2026-11-15T19:00:00Z',
      end_at: '2026-11-15T22:00:00Z',
      seats: 100,
      reserved: 85,
      checked_in: 0,
    },
  ],
};

describe('Organization', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Organization],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function render(role: RoleEnum, stats: OrganizationStats = STATS): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(Organization);
    fixture.componentRef.setInput('org', 'sala-apolo');
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne('/api/v1/organizations/sala-apolo/').flush({
      role,
      organization: {
        id: 1,
        name: 'Sala Apolo',
        slug: 'sala-apolo',
        description: '',
        created_at: '2026-10-28T10:00:00Z',
      },
    });
    // The stats request depends on the role in that first answer.
    await flushMicrotasks();
    fixture.detectChanges();
    await flushMicrotasks();
    if (role !== 'STAFF') {
      http.expectOne('/api/v1/organizations/sala-apolo/stats/').flush(stats);
    }
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('shows the organization and my role', async () => {
    const element = await render('MANAGER');

    expect(element.querySelector('h1')?.textContent).toContain('Sala Apolo');
    expect(element.textContent).toContain('Gestor');
  });

  it('links owners to member management', async () => {
    const link = (await render('OWNER')).querySelector('a[href="/org/sala-apolo/members"]');

    expect(link).toBeTruthy();
  });

  it('hides member management from other roles', async () => {
    const link = (await render('STAFF')).querySelector('a[href="/org/sala-apolo/members"]');

    expect(link).toBeNull();
  });

  it('shows organizers the headline figures', async () => {
    const element = await render('MANAGER');
    const tiles = [...element.querySelectorAll('app-stat-tile')].map((t) => t.textContent);

    expect(tiles[0]).toContain('Eventos activos');
    expect(tiles[0]).toContain('2');
    expect(tiles[1]).toContain('150');
    expect(tiles[1]).toContain('de 200 plazas');
    expect(tiles[2]).toContain('75 %');
    expect(tiles[3]).toContain('20 % de las reservas');
  });

  it('lists the upcoming events with their occupancy, linked to their management', async () => {
    const row = (await render('OWNER')).querySelector<HTMLAnchorElement>('.event-row')!;

    expect(row.getAttribute('href')).toBe('/org/sala-apolo/events/7');
    expect(row.textContent).toContain('Noche de Jazz');
    expect(row.textContent).toContain('85 %');
    expect(row.textContent).toContain('85 / 100');
    expect(row.querySelector('[role="meter"]')?.getAttribute('aria-valuetext')).toBe('85 de 100');
  });

  it('says so when nothing is coming up', async () => {
    const element = await render('OWNER', { ...STATS, upcoming: [] });

    expect(element.textContent).toContain('No hay eventos publicados por delante.');
  });

  it('never asks for stats as staff', async () => {
    const element = await render('STAFF');

    expect(element.querySelector('app-stat-tile')).toBeNull(); // http.verify() checks the call
  });
});
