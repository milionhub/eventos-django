import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  convertToParamMap,
  Router,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';
import { vi } from 'vitest';

import { RoleEnum } from '../api/models';
import { orgRoleGuard } from './auth.guards';
import { AuthService } from './auth.service';

describe('orgRoleGuard', () => {
  let role: RoleEnum | null;
  const reloadUser = vi.fn();

  beforeEach(() => {
    role = null;
    reloadUser.mockReset().mockResolvedValue(undefined);
    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: { roleIn: (slug: string) => (slug === 'sala-apolo' ? role : null), reloadUser },
        },
      ],
    });
  });

  const run = (roles: RoleEnum[], org = 'sala-apolo') =>
    TestBed.runInInjectionContext(() =>
      orgRoleGuard(roles)(
        { paramMap: convertToParamMap({ org }) } as ActivatedRouteSnapshot,
        {} as RouterStateSnapshot,
      ),
    ) as Promise<boolean | UrlTree>;
  const serialize = (result: boolean | UrlTree) =>
    TestBed.inject(Router).serializeUrl(result as UrlTree);

  it('lets in members with an allowed role', async () => {
    role = 'OWNER';

    expect(await run(['OWNER'])).toBe(true);
    expect(reloadUser).not.toHaveBeenCalled();
  });

  it('sends members with another role back to their organizations', async () => {
    role = 'STAFF';

    expect(serialize(await run(['OWNER']))).toBe('/org');
  });

  it('re-reads the memberships once before rejecting non-members', async () => {
    reloadUser.mockImplementation(async () => {
      role = 'MANAGER'; // someone added us after we signed in
    });

    expect(await run(['OWNER', 'MANAGER'])).toBe(true);
    expect(reloadUser).toHaveBeenCalledOnce();
  });

  it('rejects organizations the user does not belong to', async () => {
    expect(serialize(await run(['OWNER'], 'otra'))).toBe('/org');
  });
});
