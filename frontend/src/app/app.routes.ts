import { Routes } from '@angular/router';

import { authGuard, guestGuard, orgRoleGuard } from './core/auth/auth.guards';
import { ORGANIZERS, ROLES } from './shared/roles';

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
    path: 'events/:slug',
    title: 'Evento · #4events',
    loadComponent: () => import('./features/public-event/public-event').then((m) => m.PublicEvent),
  },
  {
    path: 'me/tickets',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        title: 'Mis entradas · #4events',
        loadComponent: () =>
          import('./features/my-tickets/my-tickets/my-tickets').then((m) => m.MyTickets),
      },
      {
        path: ':id',
        title: 'Entrada · #4events',
        loadComponent: () => import('./features/my-tickets/ticket/ticket').then((m) => m.Ticket),
      },
    ],
  },
  {
    path: 'checkin',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        title: 'Validar · #4events',
        loadComponent: () =>
          import('./features/checkin/checkin-events/checkin-events').then((m) => m.CheckinEvents),
      },
      {
        path: ':id',
        title: 'Escáner · #4events',
        loadComponent: () => import('./features/checkin/scanner/scanner').then((m) => m.Scanner),
      },
    ],
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
        path: ':org/events',
        title: 'Eventos · #4events',
        canActivate: [orgRoleGuard(ROLES)],
        loadComponent: () => import('./features/organizer/events/events').then((m) => m.Events),
      },
      {
        path: ':org/events/new',
        title: 'Nuevo evento · #4events',
        canActivate: [orgRoleGuard(ORGANIZERS)],
        loadComponent: () =>
          import('./features/organizer/event-create/event-create').then((m) => m.EventCreate),
      },
      {
        path: ':org/events/:id',
        title: 'Gestionar evento · #4events',
        canActivate: [orgRoleGuard(ORGANIZERS)],
        loadComponent: () =>
          import('./features/organizer/event-manage/event-manage').then((m) => m.EventManage),
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
