import { TestBed } from '@angular/core/testing';

import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.style.colorScheme = '';
  });

  function create(): ThemeService {
    const service = TestBed.inject(ThemeService);
    TestBed.tick(); // run the effect that applies the theme
    return service;
  }

  it('defaults to dark', () => {
    const service = create();

    expect(service.theme()).toBe('dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');
  });

  it('restores the saved theme', () => {
    localStorage.setItem('theme', 'light');

    expect(create().theme()).toBe('light');
  });

  it('toggles, applies and persists the theme', () => {
    const service = create();

    service.toggle();
    TestBed.tick();

    expect(document.documentElement.style.colorScheme).toBe('light');
    expect(localStorage.getItem('theme')).toBe('light');
  });
});
