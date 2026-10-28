import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    title: '#4events',
    loadComponent: () => import('./features/home/home').then((m) => m.Home),
  },
  {
    path: '**',
    title: 'No encontrado · #4events',
    loadComponent: () => import('./features/not-found/not-found').then((m) => m.NotFound),
  },
];
