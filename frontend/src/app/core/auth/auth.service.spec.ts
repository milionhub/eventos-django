import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthSession } from '../api/models';
import { AuthService } from './auth.service';

const SESSION: AuthSession = {
  access: 'access-1',
  user: {
    id: 1,
    email: 'ana@example.com',
    first_name: 'Ana',
    last_name: 'García',
    memberships: [],
  },
};

/** Lets pending promise callbacks run so the next request reaches HttpTestingController. */
const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));

describe('AuthService', () => {
  let auth: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('starts signed out', () => {
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.accessToken).toBeNull();
  });

  it('keeps the session in memory after logging in', async () => {
    const login = auth.login({ email: 'ana@example.com', password: 'secret' });
    const req = http.expectOne('/api/v1/auth/login/');
    expect(req.request.body).toEqual({ email: 'ana@example.com', password: 'secret' });
    req.flush(SESSION);

    expect(await login).toEqual(SESSION.user);
    expect(auth.user()).toEqual(SESSION.user);
    expect(auth.accessToken).toBe('access-1');
  });

  it('signs in right after registering', async () => {
    const register = auth.register({ email: 'ana@example.com', password: 'secret' });
    http.expectOne('/api/v1/auth/register/').flush(SESSION.user, { status: 201, statusText: '' });
    await flushMicrotasks();
    http.expectOne('/api/v1/auth/login/').flush(SESSION);

    await register;
    expect(auth.isAuthenticated()).toBe(true);
  });

  it('forgets the session on logout even if the request fails', async () => {
    const login = auth.login({ email: 'ana@example.com', password: 'secret' });
    http.expectOne('/api/v1/auth/login/').flush(SESSION);
    await login;

    const logout = auth.logout();
    http.expectOne('/api/v1/auth/logout/').error(new ProgressEvent('error'));

    await expect(logout).rejects.toBeDefined();
    expect(auth.isAuthenticated()).toBe(false);
  });

  it('shares one refresh request between concurrent callers', async () => {
    const first = auth.refresh();
    const second = auth.refresh();
    http.expectOne('/api/v1/auth/refresh/').flush(SESSION);

    expect(await first).toBe(true);
    expect(await second).toBe(true);
    expect(auth.accessToken).toBe('access-1');
  });

  it('clears the session when the refresh cookie is no longer valid', async () => {
    const refresh = auth.refresh();
    http
      .expectOne('/api/v1/auth/refresh/')
      .flush({ code: 'session_expired' }, { status: 401, statusText: 'Unauthorized' });

    expect(await refresh).toBe(false);
    expect(auth.isAuthenticated()).toBe(false);
  });
});
