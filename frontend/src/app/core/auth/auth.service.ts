import { computed, inject, Injectable, signal } from '@angular/core';

import { Api } from '../api/api';
import { authLogin, authLogout, authMe, authRefresh, authRegister } from '../api/functions';
import { AuthSession, LoginRequest, RegisterRequest, RoleEnum, SessionUser } from '../api/models';

/**
 * Session state (ADR-0003). The access token lives only in this signal (memory);
 * the refresh token is an httpOnly cookie the browser sends to /api/v1/auth/ by itself.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(Api);
  private readonly session = signal<AuthSession | null>(null);
  private refreshing: Promise<boolean> | null = null;

  readonly user = computed<SessionUser | null>(() => this.session()?.user ?? null);
  readonly isAuthenticated = computed(() => this.session() !== null);

  get accessToken(): string | null {
    return this.session()?.access ?? null;
  }

  async login(credentials: LoginRequest): Promise<SessionUser> {
    const session = await this.api.invoke(authLogin, { body: credentials });
    this.session.set(session);
    return session.user;
  }

  /** Creates the account and signs in straight away. */
  async register(data: RegisterRequest): Promise<SessionUser> {
    await this.api.invoke(authRegister, { body: data });
    return this.login({ email: data.email, password: data.password });
  }

  /** The user's role in an organization, or null if they are not a member (UX only). */
  roleIn(orgSlug: string | null): RoleEnum | null {
    const membership = this.user()?.memberships.find((m) => m.organization_slug === orgSlug);
    return membership?.role ?? null;
  }

  /** Re-reads the user (and their memberships) after something changed them. */
  async reloadUser(): Promise<void> {
    const session = this.session();
    if (!session) return;
    const user = await this.api.invoke(authMe);
    this.session.set({ ...session, user });
  }

  async logout(): Promise<void> {
    try {
      await this.api.invoke(authLogout);
    } finally {
      // Forget the session locally even if the server could not be reached.
      this.session.set(null);
    }
  }

  /**
   * Swaps the refresh cookie for a new access token. Used on startup to restore the
   * session and by the interceptor after a 401. Concurrent callers share one request,
   * because the backend rotates (and blacklists) the refresh token on every use.
   */
  refresh(): Promise<boolean> {
    this.refreshing ??= this.api
      .invoke(authRefresh)
      .then(
        (session) => {
          this.session.set(session);
          return true;
        },
        () => {
          this.session.set(null);
          return false;
        },
      )
      .finally(() => (this.refreshing = null));
    return this.refreshing;
  }
}
