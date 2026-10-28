import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { RoleEnum } from '../api/models';
import { AuthService } from './auth.service';

/** Signed-in users only; everyone else goes to login and comes back afterwards. */
export const authGuard: CanActivateFn = (_route, state) =>
  inject(AuthService).isAuthenticated() ||
  inject(Router).createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });

/** Login and register make no sense with a session: send those users home. */
export const guestGuard: CanActivateFn = () =>
  !inject(AuthService).isAuthenticated() || inject(Router).createUrlTree(['/']);

/**
 * Members of the `:org` organization with one of `roles`; others go back to their
 * organizations. Roles are re-read once in case someone added us after we signed in.
 * Only UX: the backend answers 404/403 on its own.
 */
export function orgRoleGuard(roles: readonly RoleEnum[]): CanActivateFn {
  return async (route) => {
    // inject() only works synchronously: resolve dependencies before awaiting.
    const auth = inject(AuthService);
    const router = inject(Router);
    const slug = route.paramMap.get('org');
    if (!auth.roleIn(slug)) {
      await auth.reloadUser().catch(() => undefined);
    }
    const role = auth.roleIn(slug);
    return (role !== null && roles.includes(role)) || router.createUrlTree(['/org']);
  };
}

/** Only same-app paths are valid after login, never an external URL (open redirect). */
export function safeReturnUrl(url: string | null): string {
  return url?.startsWith('/') && !url.startsWith('//') ? url : '/';
}
