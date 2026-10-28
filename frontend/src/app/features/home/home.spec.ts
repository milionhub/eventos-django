import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';

import { PublicEvent } from '../../core/api/models';
import { Home } from './home';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const URL = '/api/v1/public/events/';

const event = (slug: string, available: number): PublicEvent => ({
  slug,
  title: `Evento ${slug}`,
  location: 'Barcelona',
  image_url: '',
  start_at: '2026-11-20T18:30:00Z',
  end_at: '2026-11-20T21:30:00Z',
  organization_name: 'Sala Apolo',
  available,
});

describe('Home', () => {
  let fixture: ComponentFixture<Home>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Home],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function render(results: PublicEvent[], q?: string): Promise<HTMLElement> {
    fixture = TestBed.createComponent(Home);
    if (q) fixture.componentRef.setInput('q', q);
    fixture.detectChanges();
    await flushMicrotasks();
    const req = http.expectOne((r) => r.url === URL);
    expect(req.request.params.get('q')).toBe(q ?? null);
    req.flush({ count: results.length, results });
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('shows published events as tickets linking to their page', async () => {
    const element = await render([event('jazz', 42), event('indie', 0)]);

    const cards = element.querySelectorAll('a.ticket');
    expect(cards[0].getAttribute('href')).toBe('/events/jazz');
    expect(cards[0].textContent).toContain('42 plazas libres');
    expect(cards[1].textContent).toContain('Agotado');
  });

  it('puts the search in the URL', async () => {
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const element = await render([]);

    const input = element.querySelector<HTMLInputElement>('input[type="search"]')!;
    input.value = '  jazz ';
    input.dispatchEvent(new Event('input'));
    element.querySelector('form')!.dispatchEvent(new Event('submit'));

    expect(navigate).toHaveBeenCalledWith([], { queryParams: { q: 'jazz' } });
  });

  it('searches with the q from the URL and offers to clear it', async () => {
    const element = await render([], 'nada');

    expect(element.textContent).toContain('0 resultados para «nada»');
    expect(element.textContent).toContain('Nada por aquí');
  });
});
