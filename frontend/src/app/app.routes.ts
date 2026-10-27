import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    title: 'eventos',
    loadComponent: () => import('./features/home/home').then((m) => m.Home),
  },
  {
    path: '**',
    title: 'No encontrado · eventos',
    loadComponent: () => import('./features/not-found/not-found').then((m) => m.NotFound),
  },
];
