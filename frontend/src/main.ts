import { registerLocaleData } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

// Dates, numbers and month names in Spanish (the app's LOCALE_ID).
registerLocaleData(localeEs);

bootstrapApplication(App, appConfig).catch((err) => console.error(err));
