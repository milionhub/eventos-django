import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import { AuthSession } from '../api/models';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

const session = (access: string): AuthSession => ({
  access,
  user: { id: 1, email: 'ana@example.com', first_name: 'Ana', last_name: '' },
});

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpTesting: HttpTestingController;
  let auth: AuthService;

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpTesting = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);

    const login = auth.login({ email: 'ana@example.com', password: 'secret' });
    httpTesting.expectOne('/api/v1/auth/login/').flush(session('old-token'));
    await login;
  });

  afterEach(() => httpTesting.verify());

  it('adds the access token to API requests', () => {
    http.get('/api/v1/auth/me/').subscribe();

    const req = httpTesting.expectOne('/api/v1/auth/me/');
    expect(req.request.headers.get('Authorization')).toBe('Bearer old-token');
    req.flush({});
  });

  it('never sends the token to other hosts', () => {
    http.get('https://example.com/data').subscribe();

    const req = httpTesting.expectOne('https://example.com/data');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('refreshes an expired token once and retries the request', async () => {
    const result = firstValueFrom(http.get('/api/v1/auth/me/'));

    httpTesting.expectOne('/api/v1/auth/me/').flush(null, { status: 401, statusText: '' });
    httpTesting.expectOne('/api/v1/auth/refresh/').flush(session('new-token'));
    await flushMicrotasks();
    const retry = httpTesting.expectOne('/api/v1/auth/me/');
    expect(retry.request.headers.get('Authorization')).toBe('Bearer new-token');
    retry.flush({ ok: true });

    expect(await result).toEqual({ ok: true });
  });

  it('signs out and propagates the 401 when the refresh fails', async () => {
    const result = firstValueFrom(http.get('/api/v1/auth/me/'));

    httpTesting.expectOne('/api/v1/auth/me/').flush(null, { status: 401, statusText: '' });
    httpTesting.expectOne('/api/v1/auth/refresh/').flush(null, { status: 401, statusText: '' });

    await expect(result).rejects.toMatchObject({ status: 401 });
    expect(auth.isAuthenticated()).toBe(false);
  });
});
