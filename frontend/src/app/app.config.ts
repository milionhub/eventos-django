import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  isDevMode,
  LOCALE_ID,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { provideServiceWorker } from '@angular/service-worker';

import { routes } from './app.routes';
import { authInterceptor } from './core/auth/auth.interceptor';
import { AuthService } from './core/auth/auth.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    // Restore the session from the refresh cookie before the first route renders,
    // so guards and the header already know who is signed in.
    provideAppInitializer(() => inject(AuthService).refresh()),
    // Spanish formats; dates are shown in the browser's time zone (RNF-04).
    { provide: LOCALE_ID, useValue: 'es' },
    // PWA (RNF-02): caches the app's static files only, never the API (see ngsw-config.json).
    // Off in development, where it would serve stale builds.
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isDevMode(),
      registrationStrategy: 'registerWhenStable:30000',
    }),
  ],
};
