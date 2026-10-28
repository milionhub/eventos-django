import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';

import { PublicEventDetail } from '../../core/api/models';
import { AuthService } from '../../core/auth/auth.service';
import { PublicEvent } from './public-event';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const URL = '/api/v1/public/events/jazz/';

const DETAIL: PublicEventDetail = {
  slug: 'jazz',
  title: 'Noche de Jazz',
  description: 'Cuarteto en directo.',
  location: 'Sala Apolo, Barcelona',
  image_url: '',
  start_at: '2026-11-20T18:30:00Z',
  end_at: '2026-11-20T21:30:00Z',
  organization_name: 'Sala Apolo',
  is_finished: false,
  available: 20,
  ticket_types: [
    { id: 1, name: 'VIP', description: '', available: 0, sold_out: true },
    { id: 2, name: 'General', description: '', available: 20, sold_out: false },
  ],
};

describe('PublicEvent', () => {
  let fixture: ComponentFixture<PublicEvent>;
  let http: HttpTestingController;
  const isAuthenticated = signal(false);

  beforeEach(async () => {
    isAuthenticated.set(false);
    await TestBed.configureTestingModule({
      imports: [PublicEvent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { isAuthenticated } },
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function render(
    respond: (req: ReturnType<HttpTestingController['expectOne']>) => void,
  ): Promise<HTMLElement> {
    fixture = TestBed.createComponent(PublicEvent);
    fixture.componentRef.setInput('slug', 'jazz');
    fixture.detectChanges();
    await flushMicrotasks();
    respond(http.expectOne(URL));
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('preselects the first category with seats and disables sold-out ones', async () => {
    const element = await render((req) => req.flush(DETAIL));

    const [vip, general] = element.querySelectorAll<HTMLButtonElement>('[role="radio"]');
    expect(vip.disabled).toBe(true);
    expect(vip.textContent).toContain('Agotado');
    expect(general.getAttribute('aria-checked')).toBe('true');
  });

  it('invites visitors to sign in and come back to this event', async () => {
    const element = await render((req) => req.flush(DETAIL));

    const cta = element.querySelector('a.cta')!;
    expect(cta.getAttribute('href')).toBe('/login?returnUrl=%2Fevents%2Fjazz');
  });

  it('lets signed-in users book the selected category', async () => {
    isAuthenticated.set(true);
    const element = await render((req) => req.flush(DETAIL));

    const button = element.querySelector<HTMLButtonElement>('button.cta')!;
    expect(button.disabled).toBe(false);
    expect(button.textContent).toContain('Reservar gratis');
  });

  it('books the selected category and opens the new ticket', async () => {
    isAuthenticated.set(true);
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const element = await render((req) => req.flush(DETAIL));

    element.querySelector<HTMLButtonElement>('button.cta')!.click();
    const req = http.expectOne('/api/v1/reservations/');
    expect(req.request.body).toEqual({ ticket_type: 2 }); // General, the one with seats
    req.flush({ id: 'r1', ticket: { id: 't1', status: 'VALID' } }, { status: 201, statusText: '' });
    await fixture.whenStable();

    expect(navigate).toHaveBeenCalledWith(['/me/tickets', 't1'], { queryParams: { nueva: 1 } });
  });

  it('links to my tickets when I already have one', async () => {
    isAuthenticated.set(true);
    const element = await render((req) => req.flush(DETAIL));

    element.querySelector<HTMLButtonElement>('button.cta')!.click();
    http
      .expectOne('/api/v1/reservations/')
      .flush({ code: 'already_reserved', detail: '' }, { status: 409, statusText: '' });
    await fixture.whenStable();

    const alert = element.querySelector('[role="alert"]')!;
    expect(alert.textContent).toContain('Ya tienes una entrada');
    expect(alert.querySelector('a')?.getAttribute('href')).toBe('/me/tickets');
  });

  it('refreshes the availability when the seats run out meanwhile', async () => {
    isAuthenticated.set(true);
    const element = await render((req) => req.flush(DETAIL));

    element.querySelector<HTMLButtonElement>('button.cta')!.click();
    http
      .expectOne('/api/v1/reservations/')
      .flush({ code: 'sold_out', detail: '' }, { status: 409, statusText: '' });
    await new Promise((resolve) => setTimeout(resolve));
    http.expectOne(URL).flush({ ...DETAIL, available: 0, ticket_types: [] });
    await fixture.whenStable();

    expect(element.textContent).toContain('agotar');
  });

  it('explains when the event is not public', async () => {
    const element = await render((req) =>
      req.flush({ detail: 'No encontrado.' }, { status: 404, statusText: 'Not Found' }),
    );

    expect(element.querySelector('h1')?.textContent).toContain('no existe o ya no está publicado');
  });
});
