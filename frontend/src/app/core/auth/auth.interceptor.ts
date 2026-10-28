import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, from, switchMap, throwError } from 'rxjs';

import { AuthService } from './auth.service';

/** Endpoints that work with the refresh cookie: a 401 there must not trigger another refresh. */
const COOKIE_ENDPOINTS = ['login', 'register', 'refresh', 'logout'].map(
  (name) => `/api/v1/auth/${name}/`,
);

function withToken(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

/**
 * Adds the access token to our API calls and, when it has expired (401), refreshes it
 * once and retries. If the refresh fails the session is cleared and the 401 propagates.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.accessToken;
  const isOwnApi = req.url.startsWith('/api/');

  if (!token || !isOwnApi || COOKIE_ENDPOINTS.some((url) => req.url.endsWith(url))) {
    return next(req);
  }

  return next(withToken(req, token)).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401) {
        return throwError(() => error);
      }
      return from(auth.refresh()).pipe(
        switchMap((refreshed) =>
          refreshed && auth.accessToken
            ? next(withToken(req, auth.accessToken))
            : throwError(() => error),
        ),
      );
    }),
  );
};
