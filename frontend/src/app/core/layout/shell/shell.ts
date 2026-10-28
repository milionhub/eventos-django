import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
// Standalone directives rather than MatMenuModule: NgModules cannot be lazy-loaded by @defer.
import { MatMenu, MatMenuItem, MatMenuTrigger } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { map } from 'rxjs';

import { AuthService } from '../../auth/auth.service';
import { initials } from '../../../shared/roles';
import { ApiStatus } from '../api-status/api-status';
import { ThemeService } from '../../theme/theme.service';

interface NavItem {
  label: string;
  icon: string;
  path: string;
  /** Highlight only on this exact URL (home), not on its children. */
  exact: boolean;
}

const EVENTS: NavItem = { label: 'Eventos', icon: 'event', path: '/', exact: true };
const MY_TICKETS: NavItem = {
  label: 'Mis entradas',
  icon: 'confirmation_number',
  path: '/me/tickets',
  exact: false,
};
const ORGANIZATIONS: NavItem = {
  label: 'Organizaciones',
  icon: 'groups',
  path: '/org',
  exact: false,
};

/** App frame: sticky header, links inline on desktop and in a drawer on mobile, and a footer. */
@Component({
  selector: 'app-shell',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatSidenavModule,
    MatButtonModule,
    MatIconModule,
    MatMenu,
    MatMenuItem,
    MatMenuTrigger,
    ApiStatus,
  ],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  // Sections are added here as each phase delivers them.
  protected readonly navItems = computed<NavItem[]>(() =>
    this.auth.isAuthenticated() ? [EVENTS, MY_TICKETS, ORGANIZATIONS] : [EVENTS],
  );

  protected readonly isHandset = toSignal(
    inject(BreakpointObserver)
      .observe([Breakpoints.XSmall, Breakpoints.Small])
      .pipe(map((result) => result.matches)),
    { initialValue: false },
  );

  private readonly themeService = inject(ThemeService);
  protected readonly theme = this.themeService.theme;

  protected readonly user = this.auth.user;
  protected readonly initials = computed(() => {
    const user = this.user();
    return user ? initials(user) : '';
  });

  protected toggleTheme(): void {
    this.themeService.toggle();
  }

  protected async logout(): Promise<void> {
    await this.auth.logout();
    await this.router.navigateByUrl('/');
  }
}
