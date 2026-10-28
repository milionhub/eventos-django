import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Event, RoleEnum } from '../../../core/api/models';
import { AuthService } from '../../../core/auth/auth.service';
import { Events } from './events';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const URL = '/api/v1/organizations/sala-apolo/events/';

const event = (id: number, overrides: Partial<Event> = {}): Event => ({
  id,
  title: `Evento ${id}`,
  slug: `evento-${id}`,
  location: 'Barcelona',
  image_url: '',
  start_at: '2026-11-20T18:30:00Z',
  end_at: '2026-11-20T21:30:00Z',
  capacity: 100,
  status: 'DRAFT',
  is_finished: false,
  published_at: null,
  cancelled_at: null,
  ...overrides,
});

describe('Events', () => {
  let fixture: ComponentFixture<Events>;
  let http: HttpTestingController;

  async function render(role: RoleEnum, results: Event[]): Promise<HTMLElement> {
    await TestBed.configureTestingModule({
      imports: [Events],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { roleIn: () => role } },
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(Events);
    fixture.componentRef.setInput('org', 'sala-apolo');
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne((req) => req.url === URL).flush({ count: results.length, results });
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  afterEach(() => http.verify());

  it('lists events with their status and links organizers to manage them', async () => {
    const element = await render('MANAGER', [
      event(1, { status: 'PUBLISHED', is_finished: true }),
      event(2, { status: 'CANCELLED' }),
    ]);

    const rows = element.querySelectorAll('a.row');
    expect(rows[0].getAttribute('href')).toBe('/org/sala-apolo/events/1');
    expect(rows[0].textContent).toContain('Finalizado');
    expect(rows[1].textContent).toContain('Cancelado');
    expect(element.textContent).toContain('Nuevo evento');
  });

  it('shows STAFF a read-only list', async () => {
    const element = await render('STAFF', [event(1)]);

    expect(element.querySelector('a.row')?.getAttribute('href')).toBeNull();
    expect(element.textContent).not.toContain('Nuevo evento');
  });

  it('filters by status from the first page', async () => {
    const element = await render('OWNER', [event(1)]);

    const drafts = [...element.querySelectorAll<HTMLButtonElement>('button.filter')].find((b) =>
      b.textContent?.includes('Borradores'),
    )!;
    drafts.click();
    await flushMicrotasks();

    const req = http.expectOne((r) => r.url === URL);
    expect(req.request.params.get('status')).toBe('DRAFT');
    expect(req.request.params.get('page')).toBe('1');
    req.flush({ count: 0, results: [] });
    await fixture.whenStable();
    expect(element.textContent).toContain('No hay eventos con este estado');
  });
});
