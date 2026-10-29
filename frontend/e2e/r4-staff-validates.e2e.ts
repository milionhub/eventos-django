import { expect, test } from '@playwright/test';

import { addStaff, book, logIn, myTickets, publishedEvent, signUp, ticketToken } from './support';

// R4 — Door staff signs in, sees the events assigned to them with the door open, validates a
// ticket and keeps scanning: the same ticket the second time is refused. The camera is not
// available here, so the code goes through the manual entry, which calls the same endpoint.
test('R4: el personal de acceso valida entradas', async ({ page, request }) => {
  const event = await publishedEvent(request);
  const sara = await signUp(request, 'Sara');
  await addStaff(request, event, sara);
  const ana = await signUp(request, 'Ana');
  await book(request, ana, event.general);
  const [ticket] = await myTickets(request, ana);
  const token = await ticketToken(request, ana, ticket.id);

  await test.step('ve su evento con la puerta abierta', async () => {
    await logIn(page, sara, '/checkin');
    const card = page.getByRole('link', { name: new RegExp(event.title) });
    await expect(card.getByText('Puerta abierta')).toBeVisible();
    await card.click();
  });

  const scan = async () => {
    await page.getByPlaceholder('Código de la entrada').fill(token);
    await page.getByRole('button', { name: 'Validar' }).click();
  };

  // The full-screen answer (role="alert"), not the "Últimos escaneos" list below it.
  const result = page.getByRole('alert');

  await test.step('la entrada es válida', async () => {
    await scan();
    await expect(result).toContainText('Válida');
    await expect(result).toContainText('Ana Prueba');
    await result.click(); // "Toca para seguir"
    await expect(result).toBeHidden();
  });

  await test.step('y no entra dos veces', async () => {
    await scan();
    await expect(result).toContainText('Ya utilizada');
    await expect(result).toContainText('Entró a las');
  });
});
