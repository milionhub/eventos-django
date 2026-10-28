import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MyTicket, TicketStatusEnum } from '../../../core/api/models';
import { MyTickets } from './my-tickets';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const DAY = 24 * 3600 * 1000;

const ticket = (id: string, status: TicketStatusEnum, inDays: number): MyTicket => {
  const start = new Date(Date.now() + inDays * DAY);
  return {
    id,
    status,
    issued_at: '2026-10-28T10:00:00Z',
    checked_in_at: null,
    event: {
      slug: `evento-${id}`,
      title: `Evento ${id}`,
      image_url: '',
      location: 'Barcelona',
      start_at: start.toISOString(),
      end_at: new Date(start.getTime() + 3600 * 1000).toISOString(),
      status: 'PUBLISHED',
      organization_name: 'Sala Apolo',
    },
    ticket_type: { id: 1, name: 'General' },
    reservation: {
      id: `r-${id}`,
      status: status === 'CANCELLED' ? 'CANCELLED' : 'CONFIRMED',
      created_at: '2026-10-28T10:00:00Z',
      cancelled_at: null,
    },
  };
};

describe('MyTickets', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MyTickets],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function render(tickets: MyTicket[]): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(MyTickets);
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne('/api/v1/me/tickets/').flush(tickets);
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('splits upcoming tickets from the history', async () => {
    const element = await render([
      ticket('a', 'VALID', 5),
      ticket('b', 'CANCELLED', 7),
      ticket('c', 'VALID', -3), // event already over
      ticket('d', 'USED', -10),
    ]);

    const [upcoming, history] = element.querySelectorAll('section');
    expect(upcoming.querySelectorAll('a.row')).toHaveLength(1);
    expect(upcoming.querySelector('a.row')?.getAttribute('href')).toBe('/me/tickets/a');
    expect(history.textContent).toContain('Cancelada');
    expect(history.textContent).toContain('Finalizado');
    expect(history.textContent).toContain('Utilizada');
  });

  it('invites to browse events when there is nothing upcoming', async () => {
    const element = await render([]);

    expect(element.textContent).toContain('No tienes entradas para próximos eventos');
    expect(element.querySelector('a[href="/"]')).toBeTruthy();
    expect(element.textContent).not.toContain('Historial');
  });
});
