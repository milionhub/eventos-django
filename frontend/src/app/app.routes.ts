import { Routes } from '@angular/router';

import { guestGuard } from './core/auth/auth.guards';

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
    path: '**',
    title: 'No encontrado · #4events',
    loadComponent: () => import('./features/not-found/not-found').then((m) => m.NotFound),
  },
];
