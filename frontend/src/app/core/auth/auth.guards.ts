import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

/** Signed-in users only; everyone else goes to login and comes back afterwards. */
export const authGuard: CanActivateFn = (_route, state) =>
  inject(AuthService).isAuthenticated() ||
  inject(Router).createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });

/** Login and register make no sense with a session: send those users home. */
export const guestGuard: CanActivateFn = () =>
  !inject(AuthService).isAuthenticated() || inject(Router).createUrlTree(['/']);

/** Only same-app paths are valid after login, never an external URL (open redirect). */
export function safeReturnUrl(url: string | null): string {
  return url?.startsWith('/') && !url.startsWith('//') ? url : '/';
}
