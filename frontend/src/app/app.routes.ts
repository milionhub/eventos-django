import { Routes } from '@angular/router';

import { authGuard, guestGuard, orgRoleGuard } from './core/auth/auth.guards';
import { ROLES } from './shared/roles';

export const routes: Routes = [
  {
    path: '',
    title: '#4events',
    loadComponent: () => import('./features/home/home').then((m) => m.Home),
  },
  {
    path: 'login',
    title: 'Entrar · #4events',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
  },
  {
    path: 'register',
    title: 'Crear cuenta · #4events',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/register/register').then((m) => m.Register),
  },
  {
    path: 'org',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        title: 'Organizaciones · #4events',
        loadComponent: () =>
          import('./features/organizer/organizations/organizations').then((m) => m.Organizations),
      },
      {
        path: ':org',
        title: 'Organización · #4events',
        canActivate: [orgRoleGuard(ROLES)],
        loadComponent: () =>
          import('./features/organizer/organization/organization').then((m) => m.Organization),
      },
      {
        path: ':org/members',
        title: 'Miembros · #4events',
        canActivate: [orgRoleGuard(['OWNER'])],
        loadComponent: () => import('./features/organizer/members/members').then((m) => m.Members),
      },
    ],
  },
  {
    path: '**',
    title: 'No encontrado · #4events',
    loadComponent: () => import('./features/not-found/not-found').then((m) => m.NotFound),
  },
];
