import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree } from '@angular/router';

import { authGuard, guestGuard, safeReturnUrl } from './auth.guards';
import { AuthService } from './auth.service';

describe('auth guards', () => {
  const isAuthenticated = signal(false);

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: AuthService, useValue: { isAuthenticated } }],
    });
  });

  const run = (guard: typeof authGuard, url = '/me/tickets') =>
    TestBed.runInInjectionContext(() =>
      guard({} as ActivatedRouteSnapshot, { url } as RouterStateSnapshot),
    );
  const serialize = (result: unknown) => TestBed.inject(Router).serializeUrl(result as UrlTree);

  it('authGuard lets signed-in users through', () => {
    isAuthenticated.set(true);
    expect(run(authGuard)).toBe(true);
  });

  it('authGuard sends visitors to login and remembers where they were going', () => {
    isAuthenticated.set(false);
    expect(serialize(run(authGuard))).toBe('/login?returnUrl=%2Fme%2Ftickets');
  });

  it('guestGuard sends signed-in users home', () => {
    isAuthenticated.set(true);
    expect(serialize(run(guestGuard))).toBe('/');
  });

  it('guestGuard lets visitors through', () => {
    isAuthenticated.set(false);
    expect(run(guestGuard)).toBe(true);
  });

  it.each([
    ['/events/jazz', '/events/jazz'],
    [null, '/'],
    ['https://evil.example', '/'],
    ['//evil.example', '/'],
  ])('safeReturnUrl(%s) → %s', (input, expected) => {
    expect(safeReturnUrl(input)).toBe(expected);
  });
});
