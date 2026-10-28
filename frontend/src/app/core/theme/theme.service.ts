import { DOCUMENT } from '@angular/common';
import { effect, inject, Injectable, signal } from '@angular/core';

export type Theme = 'dark' | 'light';

/** Must match the inline script in index.html, which applies the theme before Angular boots. */
const STORAGE_KEY = 'theme';

/** Light/dark theme. Dark is the brand default; the user's choice is kept in localStorage. */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);
  private readonly storage = this.document.defaultView?.localStorage;

  readonly theme = signal<Theme>(this.storage?.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark');

  constructor() {
    effect(() => {
      const theme = this.theme();
      // Material's system tokens use light-dark(), so switching color-scheme re-themes everything.
      this.document.documentElement.style.colorScheme = theme;
      this.storage?.setItem(STORAGE_KEY, theme);
    });
  }

  toggle(): void {
    this.theme.update((theme) => (theme === 'dark' ? 'light' : 'dark'));
  }
}
