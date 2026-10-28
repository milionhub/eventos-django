import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { routes } from './app.routes';

describe('routes', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    });
  });

  it('shows the home page at /', async () => {
    const harness = await RouterTestingHarness.create('/');

    expect(harness.routeNativeElement?.querySelector('h1')?.textContent).toContain(
      'Próximos eventos',
    );
  });

  it('shows the not-found page for unknown URLs', async () => {
    const harness = await RouterTestingHarness.create('/no-existe');

    expect(TestBed.inject(Router).url).toBe('/no-existe');
    expect(harness.routeNativeElement?.querySelector('h1')?.textContent).toContain(
      'Página no encontrada',
    );
  });
});
