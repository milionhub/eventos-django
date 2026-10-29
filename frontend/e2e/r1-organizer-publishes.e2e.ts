import { expect, test } from '@playwright/test';

import { PASSWORD, unique } from './support';

// R1 — An organizer signs up, creates an organization, a draft event with its categories and
// publishes it: it then shows up in the public listing. Every step through the UI.
test('R1: el organizador crea y publica un evento', async ({ page }) => {
  const email = `${unique('olga')}@e2e.test`;
  const orgName = unique('Sala');
  const title = unique('Concierto');

  await test.step('se registra', async () => {
    await page.goto('/register');
    await page.getByLabel('Nombre', { exact: true }).fill('Olga');
    await page.getByLabel('Apellidos').fill('Organiza');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Contraseña', { exact: true }).fill(PASSWORD);
    await page.getByRole('button', { name: 'Crear cuenta' }).click();
    await expect(page).not.toHaveURL(/\/register/);
  });

  await test.step('crea una organización y pasa a ser su propietaria', async () => {
    await page.goto('/org');
    await page.getByRole('button', { name: 'Nueva organización' }).click();
    await page.getByLabel('Nombre', { exact: true }).fill(orgName);
    await page.getByRole('button', { name: 'Crear organización' }).click();
    await expect(page.getByRole('heading', { name: orgName })).toBeVisible();
    await expect(page.getByText('Propietario')).toBeVisible();
  });

  await test.step('crea un evento, que queda en borrador', async () => {
    await page
      .getByRole('link', { name: /Eventos/ })
      .last()
      .click();
    await page.getByRole('link', { name: 'Nuevo evento' }).click();
    await page.getByLabel('Título').fill(title);
    await page.getByLabel('Ubicación').fill('Calle Mayor 1, Madrid');

    // Next week, picked in the calendar (the day field is read-only on purpose).
    const day = new Date(Date.now() + 7 * 86_400_000);
    await page
      .getByRole('button', { name: /Open calendar|Abrir calendario/i })
      .first()
      .click();
    if (day.getMonth() !== new Date().getMonth()) {
      await page.getByRole('button', { name: /Next month|Mes siguiente/i }).click();
    }
    await page
      .locator('.mat-calendar-body-cell:not(.mat-calendar-body-disabled)')
      .getByText(String(day.getDate()), { exact: true })
      .click();
    await page.getByLabel('Hora de inicio').fill('20:30');
    await page.getByLabel('Hora de inicio').press('Tab');
    await page.getByRole('button', { name: '3 h' }).click();
    await page.getByLabel('Aforo total').fill('100');
    await page.getByRole('button', { name: 'Crear borrador' }).click();

    await expect(page.getByRole('heading', { name: title })).toBeVisible();
    await expect(page.getByText('Para publicar falta:')).toBeVisible();
  });

  await test.step('añade las categorías General y VIP', async () => {
    const form = page.locator('form').filter({ hasText: 'Nueva categoría' });
    for (const [name, capacity] of [
      ['General', '80'],
      ['VIP', '20'],
    ]) {
      await form.getByLabel('Nombre', { exact: true }).fill(name);
      await form.getByLabel('Cupo').fill(capacity);
      await form.getByRole('button', { name: 'Añadir categoría' }).click();
      await expect(page.getByRole('listitem').filter({ hasText: name }).first()).toBeVisible();
    }
  });

  await test.step('lo publica y aparece en el listado público', async () => {
    await page.getByRole('button', { name: 'Publicar' }).click();
    await expect(page.getByRole('link', { name: 'Ver página pública' })).toBeVisible();

    await page.goto('/');
    await page.getByRole('searchbox', { name: 'Buscar eventos por nombre o lugar' }).fill(title);
    await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { name: title })).toBeVisible();
  });
});
