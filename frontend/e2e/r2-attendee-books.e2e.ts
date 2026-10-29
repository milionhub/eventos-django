import { expect, test } from '@playwright/test';

import { PASSWORD, publishedEvent, unique } from './support';

// R2 — Someone without an account finds the event, is asked to sign up, comes back to the
// event, books and sees the ticket with its QR.
test('R2: el asistente reserva una entrada', async ({ page, request }) => {
  const event = await publishedEvent(request);

  await test.step('ve el evento sin sesión, con sus categorías y plazas', async () => {
    await page.goto('/');
    await page
      .getByRole('searchbox', { name: 'Buscar eventos por nombre o lugar' })
      .fill(event.title);
    await page.keyboard.press('Enter');
    await page.getByRole('link', { name: new RegExp(event.title) }).click();
    await expect(page.getByRole('heading', { name: event.title })).toBeVisible();
    await expect(page.getByRole('radio', { name: /General.*20 libres/ })).toBeVisible();
  });

  await test.step('al reservar se le pide cuenta y vuelve al evento', async () => {
    await page.getByRole('link', { name: 'Créala gratis' }).click();
    await page.getByLabel('Nombre', { exact: true }).fill('Ana');
    await page.getByLabel('Apellidos').fill('Asiste');
    await page.getByLabel('Email').fill(`${unique('ana')}@e2e.test`);
    await page.getByLabel('Contraseña', { exact: true }).fill(PASSWORD);
    await page.getByRole('button', { name: 'Crear cuenta' }).click();
    await expect(page).toHaveURL(new RegExp(`/events/${event.slug}$`));
  });

  await test.step('elige la categoría, confirma y ve su entrada con el QR', async () => {
    await page.getByRole('radio', { name: /General/ }).click();
    await page.getByRole('button', { name: 'Reservar gratis' }).click();
    await expect(page.getByText('¡Reserva confirmada! Esta es tu entrada.')).toBeVisible();
    await expect(page.getByRole('img', { name: 'Código QR de la entrada' })).toBeVisible();
    await expect(page.getByText('Válida')).toBeVisible();
  });

  await test.step('la entrada queda en «Mis entradas»', async () => {
    await page.getByRole('link', { name: 'Mis entradas' }).first().click();
    await expect(page.getByRole('link', { name: new RegExp(event.title) })).toBeVisible();
  });
});
