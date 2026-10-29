import { readFile } from 'node:fs/promises';

import { expect, test } from '@playwright/test';

import { book, logIn, myTickets, publishedEvent, signUp, ticketToken } from './support';

// R5 — The organizer checks occupancy and check-ins on the dashboard and in the event, lists
// the attendees and downloads them as CSV.
test('R5: el organizador consulta resultados', async ({ page, request }) => {
  const event = await publishedEvent(request);
  const ana = await signUp(request, 'Ana');
  const bruno = await signUp(request, 'Bruno');
  await book(request, ana, event.general);
  await book(request, bruno, event.general);
  const [ticket] = await myTickets(request, ana);
  const scan = await request.post(`/api/v1/checkin/events/${event.id}/scan/`, {
    headers: { Authorization: `Bearer ${event.owner.access}` },
    data: { token: await ticketToken(request, ana, ticket.id) },
  });
  expect((await scan.json()).result).toBe('VALID');

  await test.step('el dashboard muestra ocupación y accesos', async () => {
    await logIn(page, event.owner, `/org/${event.org}`);
    const row = page.getByRole('link', { name: new RegExp(event.title) });
    await expect(row).toContainText('10 %'); // 2 of 20
    await expect(row).toContainText('2 / 20');
    await expect(row).toContainText('1 dentro');
    await row.click();
  });

  await test.step('las stats del evento, por categoría', async () => {
    await page.getByRole('tab', { name: 'Stats' }).click();
    await expect(page.getByRole('meter').first()).toBeVisible();
    await expect(page.getByText('1 escaneo en total.')).toBeVisible();
  });

  await test.step('el listado de asistentes, con búsqueda', async () => {
    await page.getByRole('tab', { name: 'Asistentes' }).click();
    await expect(page.getByText(ana.email)).toBeVisible();
    await expect(page.getByText(bruno.email)).toBeVisible();
    await page.getByLabel('Buscar').fill('Bruno');
    await expect(page.getByText(ana.email)).toBeHidden();
    await expect(page.getByText(bruno.email)).toBeVisible();
    await page.getByLabel('Buscar').clear();
  });

  await test.step('exporta los asistentes a CSV', async () => {
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Exportar CSV' }).click();
    const file = await download;
    expect(file.suggestedFilename()).toBe(`asistentes-${event.slug}.csv`);
    const csv = await readFile(await file.path(), 'utf8');
    const lines = csv.trim().split(/\r?\n/);
    expect(lines).toHaveLength(3); // header + Ana + Bruno
    expect(lines[0]).toContain('Nombre;Apellidos;Email');
    expect(csv).toContain(ana.email);
    expect(csv).toContain(bruno.email);
  });
});
