import { expect, test } from '@playwright/test';

import { book, logIn, publishedEvent, signUp } from './support';

// R3 — The attendee cancels from "Mis entradas" (two clicks, the second one confirms) and the
// seat goes back on sale.
test('R3: el asistente cancela su reserva', async ({ page, request }) => {
  const event = await publishedEvent(request);
  const ana = await signUp(request, 'Ana');
  await book(request, ana, event.general);

  await test.step('cancela desde su entrada', async () => {
    await logIn(page, ana, '/me/tickets');
    await page.getByRole('link', { name: new RegExp(event.title) }).click();
    await page.getByRole('button', { name: 'Cancelar reserva' }).click();
    await page.getByRole('button', { name: '¿Seguro? Cancelar reserva' }).click();
    await expect(page.getByText('Entrada cancelada')).toBeVisible();
  });

  await test.step('la plaza vuelve a estar libre', async () => {
    await page.goto(`/events/${event.slug}`);
    await expect(page.getByRole('radio', { name: /General.*20 libres/ })).toBeVisible();
  });
});
