import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiStatus } from './api-status';

describe('ApiStatus', () => {
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ApiStatus],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpTesting.verify());

  async function renderWith(
    respond: (req: ReturnType<HttpTestingController['expectOne']>) => void,
  ): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(ApiStatus);
    fixture.detectChanges();
    await Promise.resolve(); // let the resource loader issue the request
    respond(httpTesting.expectOne('/api/v1/health/'));
    await fixture.whenStable();
    return (fixture.nativeElement as HTMLElement).querySelector('[role="status"]')!;
  }

  it('reports API and database as operational', async () => {
    const status = await renderWith((req) => req.flush({ api: true, database: true }));

    expect(status.dataset['status']).toBe('ok');
  });

  it('reports the database as down on 503', async () => {
    const status = await renderWith((req) =>
      req.flush({ api: true, database: false }, { status: 503, statusText: 'Service Unavailable' }),
    );

    expect(status.dataset['status']).toBe('database-down');
  });

  it('reports the API as unreachable on network errors', async () => {
    const status = await renderWith((req) => req.error(new ProgressEvent('error')));

    expect(status.dataset['status']).toBe('api-down');
  });
});
