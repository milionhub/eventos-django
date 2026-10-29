import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Attendee, PaginatedAttendeeList } from '../../../core/api/models';
import { EventAttendees } from './event-attendees';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const BASE = '/api/v1/organizations/sala-apolo/events/7/';

function attendee(overrides: Partial<Attendee> = {}): Attendee {
  return {
    id: 'r-1',
    status: 'CONFIRMED',
    created_at: '2026-10-20T10:00:00Z',
    cancelled_at: null,
    user: { id: 1, first_name: 'Ana', last_name: 'Gómez', email: 'ana@example.com' },
    ticket_type: { id: 1, name: 'General' },
    ticket: { id: 't-1', status: 'VALID', checked_in_at: null },
    ...overrides,
  };
}

function page(results: Attendee[], extra: Partial<PaginatedAttendeeList> = {}) {
  return { count: results.length, next: null, previous: null, results, ...extra };
}

describe('EventAttendees', () => {
  let http: HttpTestingController;
  let fixture: ComponentFixture<EventAttendees>;
  const element = () => fixture.nativeElement as HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventAttendees],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function settle(): Promise<void> {
    await flushMicrotasks();
    fixture.detectChanges();
  }

  async function render(list = page([attendee()]), cancellable = true): Promise<void> {
    fixture = TestBed.createComponent(EventAttendees);
    fixture.componentRef.setInput('org', 'sala-apolo');
    fixture.componentRef.setInput('eventId', 7);
    fixture.componentRef.setInput('eventSlug', 'noche-de-jazz');
    fixture.componentRef.setInput('cancellable', cancellable);
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne(`${BASE}reservations/?page=1`).flush(list);
    await settle();
  }

  it('lists each attendee with category and ticket status', async () => {
    await render(
      page([
        attendee(),
        attendee({
          id: 'r-2',
          user: { id: 2, first_name: '', last_name: '', email: 'x@example.com' },
          ticket: { id: 't-2', status: 'USED', checked_in_at: '2026-11-15T19:14:00Z' },
        }),
      ]),
    );
    const rows = element().querySelectorAll('.attendee');

    expect(rows[0].textContent).toContain('Ana Gómez');
    expect(rows[0].textContent).toContain('ana@example.com');
    expect(rows[0].textContent).toContain('General');
    expect(rows[0].textContent).toContain('Válida');
    expect(rows[1].textContent).toContain('Sin nombre');
    expect(rows[1].textContent).toContain('Utilizada');
    expect(element().textContent).toContain('2 reservas');
  });

  it('searches after a pause in typing and goes back to page 1', async () => {
    await render(page([attendee()], { count: 45, next: 'n' }));
    const input = element().querySelector<HTMLInputElement>('input[formcontrolname="q"]')!;

    input.value = ' ana ';
    input.dispatchEvent(new Event('input'));
    await wait(100);
    await settle();
    http.expectNone(() => true); // still typing
    await wait(300);
    await settle();

    http.expectOne(`${BASE}reservations/?page=1&q=ana`).flush(page([]));
    await settle();
    expect(element().textContent).toContain('Nadie coincide con la búsqueda.');
  });

  it('pages through long lists', async () => {
    await render(page([attendee()], { count: 45, next: 'n' }));

    expect(element().textContent).toContain('1–20 de 45');
    const next = [...element().querySelectorAll('.pager button')][1] as HTMLButtonElement;
    next.click();
    await settle();

    http.expectOne(`${BASE}reservations/?page=2`).flush(page([attendee()], { count: 45 }));
  });

  it('cancels after a second click and tells the parent', async () => {
    await render();
    const changed = vi.fn();
    fixture.componentInstance.changed.subscribe(changed);
    const button = () => element().querySelector<HTMLButtonElement>('.attendee button')!;

    button().click();
    fixture.detectChanges();
    expect(button().textContent).toContain('¿Seguro? Cancelar');
    http.expectNone(`${BASE}reservations/r-1/cancel/`);

    button().click();
    await settle();
    http.expectOne({ method: 'POST', url: `${BASE}reservations/r-1/cancel/` }).flush({});
    await settle();
    http.expectOne(`${BASE}reservations/?page=1`).flush(page([]));
    await settle();

    expect(changed).toHaveBeenCalled();
    expect(element().textContent).toContain('Reserva de Ana Gómez cancelada.');
  });

  it('offers no cancel button when the event no longer allows it or the ticket is used', async () => {
    await render(page([attendee()]), false);
    expect(element().querySelector('.attendee button')).toBeNull();
  });

  it('downloads the CSV with the token, the filters and the browser time zone', async () => {
    await render();
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    URL.createObjectURL = vi.fn(() => 'blob:csv');
    URL.revokeObjectURL = vi.fn();

    element().querySelector<HTMLButtonElement>('.export')!.click();
    await settle();
    const request = http.expectOne((r) => r.url === `${BASE}attendees.csv`);
    expect(request.request.params.get('tz')).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone);
    expect(request.request.headers.get('Accept')).toBe('text/csv');
    request.flush(new Blob(['csv']));
    await settle();

    const link = click.mock.contexts[0] as HTMLAnchorElement;
    expect(link.download).toBe('asistentes-noche-de-jazz.csv');
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:csv');
    click.mockRestore();
  });

  it('exports what the search box says, even before the list catches up', async () => {
    await render();
    const input = element().querySelector<HTMLInputElement>('input[formcontrolname="q"]')!;
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    URL.createObjectURL = vi.fn(() => 'blob:csv');
    URL.revokeObjectURL = vi.fn();

    input.value = ' bruno ';
    input.dispatchEvent(new Event('input'));
    element().querySelector<HTMLButtonElement>('.export')!.click(); // no pause after typing
    await settle();

    const request = http.expectOne((r) => r.url === `${BASE}attendees.csv`);
    expect(request.request.params.get('q')).toBe('bruno');
    request.flush(new Blob(['csv']));
    await settle();
    click.mockRestore();
  });
});
