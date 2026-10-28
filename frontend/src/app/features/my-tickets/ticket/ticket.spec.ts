import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';

import { MyTicketDetail, TicketStatusEnum } from '../../../core/api/models';
import { AuthService } from '../../../core/auth/auth.service';
import { Ticket } from './ticket';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const URL_DETAIL = '/api/v1/me/tickets/t1/';

const detail = (status: TicketStatusEnum, can_cancel = true): MyTicketDetail => ({
  id: 't1',
  status,
  token: 'secret-token',
  issued_at: '2026-10-28T10:00:00Z',
  checked_in_at: null,
  cancel_deadline: '2026-12-12T14:00:00Z',
  can_cancel,
  event: {
    slug: 'indie',
    title: 'Indie Norte Fest',
    location: 'Bilbao',
    start_at: '2026-12-12T16:00:00Z',
    end_at: '2026-12-13T00:00:00Z',
    status: 'PUBLISHED',
    organization_name: 'Festival Indie Norte',
  },
  ticket_type: { id: 4, name: 'Early Bird' },
  reservation: {
    id: 'r1',
    status: status === 'CANCELLED' ? 'CANCELLED' : 'CONFIRMED',
    created_at: '2026-10-28T10:00:00Z',
    cancelled_at: null,
  },
});

describe('Ticket', () => {
  let fixture: ComponentFixture<Ticket>;
  let http: HttpTestingController;
  const createObjectURL = vi.fn(() => 'blob:qr');
  const revokeObjectURL = vi.fn();

  beforeEach(async () => {
    // jsdom has no object URLs.
    createObjectURL.mockClear();
    revokeObjectURL.mockClear();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    await TestBed.configureTestingModule({
      imports: [Ticket],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: { user: signal({ first_name: 'Laura', last_name: 'Gómez', email: 'l@x.es' }) },
        },
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const element = () => fixture.nativeElement as HTMLElement;

  async function settle(): Promise<void> {
    await flushMicrotasks();
    fixture.detectChanges();
    await flushMicrotasks();
  }

  async function render(ticket: MyTicketDetail, nueva?: string): Promise<void> {
    fixture = TestBed.createComponent(Ticket);
    fixture.componentRef.setInput('id', 't1');
    if (nueva) fixture.componentRef.setInput('nueva', nueva);
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne(URL_DETAIL).flush(ticket);
    await settle();
  }

  it('downloads the QR with the API client and shows it as a blob URL', async () => {
    await render(detail('VALID'), '1');

    const req = http.expectOne(`${URL_DETAIL}qr.svg`);
    expect(req.request.responseType).toBe('blob');
    expect(req.request.url).not.toContain('secret-token'); // never in a URL
    req.flush(new Blob(['<svg/>'], { type: 'image/svg+xml' }));
    await settle();

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(element().querySelector('.qr-frame img')?.getAttribute('src')).toBe('blob:qr');
    expect(element().textContent).toContain('¡Reserva confirmada!');
    expect(element().textContent).toContain('Laura Gómez');
  });

  it('frees the blob URL when leaving the page', async () => {
    await render(detail('VALID'));
    http.expectOne(`${URL_DETAIL}qr.svg`).flush(new Blob(['<svg/>']));
    await settle();

    fixture.destroy();

    expect(revokeObjectURL).toHaveBeenCalledWith('blob:qr');
  });

  it('shows no QR for a cancelled ticket', async () => {
    await render(detail('CANCELLED', false));

    http.expectNone(`${URL_DETAIL}qr.svg`);
    expect(element().textContent).toContain('Entrada cancelada');
    expect(element().textContent).not.toContain('Cancelar reserva');
  });

  it('asks before cancelling and then refreshes the ticket', async () => {
    await render(detail('VALID'));
    http.expectOne(`${URL_DETAIL}qr.svg`).flush(new Blob(['<svg/>']));
    await settle();
    const button = () => element().querySelector<HTMLButtonElement>('.cancel button')!;

    button().click();
    await settle();
    http.expectNone('/api/v1/reservations/r1/cancel/');
    expect(button().textContent).toContain('¿Seguro?');

    button().click();
    http.expectOne('/api/v1/reservations/r1/cancel/').flush({});
    await settle();
    http.expectOne(URL_DETAIL).flush(detail('CANCELLED', false));
    await settle();

    expect(element().textContent).toContain('Entrada cancelada');
  });

  it('explains when the cancellation window has closed', async () => {
    await render(detail('VALID', false));
    http.expectOne(`${URL_DETAIL}qr.svg`).flush(new Blob(['<svg/>']));
    await settle();

    expect(element().textContent).toContain('El plazo para cancelar terminó');
    expect(element().querySelector('.cancel button')).toBeNull();
  });
});
