import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { computed, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { SessionUser } from '../../api/models';
import { AuthService } from '../../auth/auth.service';
import { Shell } from './shell';

describe('Shell', () => {
  const user = signal<SessionUser | null>(null);

  beforeEach(async () => {
    user.set(null);
    await TestBed.configureTestingModule({
      imports: [Shell],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(), // the footer's API status light
        { provide: AuthService, useValue: { user, isAuthenticated: computed(() => !!user()) } },
      ],
    }).compileComponents();
  });

  async function render(): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(Shell);
    fixture.detectChanges();
    await new Promise((resolve) => setTimeout(resolve));
    // Answer the footer's /health/ call so the fixture can become stable.
    TestBed.inject(HttpTestingController)
      .match('/api/v1/health/')
      .forEach((req) => req.flush({ api: true, database: true }));
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('renders the brand linking to home', async () => {
    const brand = (await render()).querySelector('a.brand');

    expect(brand?.textContent).toContain('#4events');
    expect(brand?.getAttribute('href')).toBe('/');
  });

  it('renders a main landmark for the routed content', async () => {
    expect((await render()).querySelector('main router-outlet')).toBeTruthy();
  });

  it('toggles the theme from the header', async () => {
    const element = await render();
    const toggle = element.querySelector<HTMLButtonElement>('button.theme-toggle')!;
    const before = toggle.getAttribute('aria-label');

    toggle.click();
    await new Promise((resolve) => setTimeout(resolve));

    expect(toggle.getAttribute('aria-label')).not.toBe(before);
  });

  it('offers to sign in when there is no session', async () => {
    const element = await render();

    expect(element.querySelector('a.sign-in')?.getAttribute('href')).toBe('/login');
    expect(element.querySelector('button.account')).toBeNull();
  });

  it("shows the user's initials when signed in", async () => {
    user.set({
      id: 1,
      email: 'ana@example.com',
      first_name: 'Ana',
      last_name: 'García',
      memberships: [],
    });
    const element = await render();

    expect(element.querySelector('.avatar')?.textContent).toBe('AG');
    expect(element.querySelector('a.sign-in')).toBeNull();
  });

  it('links to organizations only when signed in', async () => {
    const link = (element: HTMLElement) => element.querySelector('nav a[href="/org"]');
    expect(link(await render())).toBeNull();

    user.set({ id: 1, email: 'ana@example.com', first_name: '', last_name: '', memberships: [] });

    expect(link(await render())).toBeTruthy();
  });
});
