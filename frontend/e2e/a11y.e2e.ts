import AxeBuilder from '@axe-core/playwright';
import { expect, Page, test } from '@playwright/test';

import {
  addStaff,
  book,
  logIn,
  myTickets,
  Person,
  publishedEvent,
  signUp,
  ticketToken,
} from './support';

// Automated WCAG 2.1 AA checks (axe) on every screen of the 5 journeys, in both themes.
// axe finds what a machine can (contrast, names, roles, labels…): about a third of the
// real problems. Keyboard use has its own test in keyboard.e2e.ts.

const WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

// One axe pass takes a few seconds and the organizer test runs eleven of them.
test.describe.configure({ timeout: 120_000 });

async function check(page: Page, path: string, ready: string) {
  await page.goto(path);
  await expect(page.getByText(ready).first()).toBeVisible();
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  const summary = violations.map(
    (v) =>
      `${v.id} (${v.impact}): ${v.help} → ` +
      v.nodes
        .map((n) => `${n.target.join(' ')} [${n.failureSummary?.split(/\n/)[1]?.trim()}]`)
        .join(' | '),
  );
  expect.soft(summary, `${path}`).toEqual([]);
}

for (const theme of ['dark', 'light'] as const) {
  test.describe(`tema ${theme === 'dark' ? 'oscuro' : 'claro'}`, () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((value) => localStorage.setItem('theme', value), theme);
    });

    test('pantallas públicas y del asistente', async ({ page, request }) => {
      const event = await publishedEvent(request);
      const ana: Person = await signUp(request, 'Ana');
      await book(request, ana, event.general);
      const [ticket] = await myTickets(request, ana);

      await check(page, '/', 'Próximos');
      await check(page, `/events/${event.slug}`, event.title);
      await check(page, '/login', 'Bienvenido de nuevo');
      await check(page, '/register', 'Crea tu cuenta');

      await logIn(page, ana);
      await check(page, '/me/tickets', event.title);
      await check(page, `/me/tickets/${ticket.id}`, event.title);
    });

    test('pantallas del personal de acceso', async ({ page, request }) => {
      const event = await publishedEvent(request);
      const sara = await signUp(request, 'Sara');
      await addStaff(request, event, sara);

      await logIn(page, sara);
      await check(page, '/checkin', event.title);
      await check(page, `/checkin/${event.id}`, '¿No lee el QR?');
    });

    test('pantallas del organizador', async ({ page, request }) => {
      const event = await publishedEvent(request);
      const ana = await signUp(request, 'Ana');
      await book(request, ana, event.general);
      const [ticket] = await myTickets(request, ana);
      await request.post(`/api/v1/checkin/events/${event.id}/scan/`, {
        headers: { Authorization: `Bearer ${event.owner.access}` },
        data: { token: await ticketToken(request, ana, ticket.id) },
      });
      const manage = `/org/${event.org}/events/${event.id}`;

      await logIn(page, event.owner);
      await check(page, '/org', 'Tu espacio de organizador');
      await check(page, `/org/${event.org}`, 'Resumen');
      await check(page, `/org/${event.org}/events`, event.title);
      await check(page, `/org/${event.org}/events/new`, 'Crear borrador');
      await check(page, `/org/${event.org}/members`, 'Olga');
      await check(page, manage, 'Título');
      await check(page, `${manage}?tab=entradas`, 'General');
      await check(page, `${manage}?tab=staff`, 'Asignar personal');
      await check(page, `${manage}?tab=asistentes`, ana.email);
      await check(page, `${manage}?tab=stats`, 'escaneo');
    });
  });
}
