import { expect, Locator, Page, test } from '@playwright/test';

import { book, PASSWORD, publishedEvent, signUp } from './support';

// Keyboard only: every control is reached with Tab, shows where the focus is, and works with
// Enter or Space. Desktop only: phones are used by touch.
test.skip(({ isMobile }) => isMobile, 'solo con teclado físico');

/** Presses Tab until `target` has the focus, then checks that the focus can be seen. */
async function tabTo(page: Page, target: Locator, maxPresses = 40) {
  for (let i = 0; i < maxPresses; i++) {
    await page.keyboard.press('Tab');
    if (await target.evaluate((el) => el === document.activeElement).catch(() => false)) {
      const ring = await target.evaluate((el) => {
        // Material text fields show the focus on the field itself: a 2 px accent border.
        const field = el.closest('.mat-mdc-form-field');
        if (field) return field.classList.contains('mat-focused');
        const style = getComputedStyle(el);
        return style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0;
      });
      expect(ring, `el foco tiene que verse: ${target}`).toBe(true);
      return;
    }
  }
  throw new Error(`No se llega con Tab a ${target}`);
}

test('el enlace «Saltar al contenido» es lo primero y salta la cabecera', async ({ page }) => {
  await page.goto('/');
  const skip = page.getByRole('link', { name: 'Saltar al contenido' });

  await page.keyboard.press('Tab');
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();
  await page.keyboard.press('Enter');

  await expect(page.locator('main')).toBeFocused();
  await expect(page).toHaveURL(/\/$/); // the router did not navigate
  await page.keyboard.press('Tab');
  const focusedInHeader = await page.evaluate(() => !!document.activeElement?.closest('header'));
  expect(focusedInHeader).toBe(false);
});

test('reservar y cancelar sin ratón', async ({ page, request }) => {
  const event = await publishedEvent(request);
  const ana = await signUp(request, 'Ana');

  await test.step('inicia sesión', async () => {
    await page.goto('/login');
    await tabTo(page, page.getByLabel('Email'));
    await page.keyboard.type(ana.email);
    await tabTo(page, page.getByLabel('Contraseña', { exact: true }));
    await page.keyboard.type(PASSWORD);
    await page.keyboard.press('Enter');
    await expect(page).not.toHaveURL(/\/login/);
  });

  await test.step('elige categoría y reserva', async () => {
    await page.goto(`/events/${event.slug}`);
    const general = page.getByRole('radio', { name: /General/ });
    await tabTo(page, general);
    await page.keyboard.press('Space');
    await expect(general).toHaveAttribute('aria-checked', 'true');
    await tabTo(page, page.getByRole('button', { name: 'Reservar gratis' }));
    await page.keyboard.press('Enter');
    await expect(page.getByText('¡Reserva confirmada! Esta es tu entrada.')).toBeVisible();
  });

  await test.step('cancela (dos pulsaciones, como los dos clics)', async () => {
    await tabTo(page, page.getByRole('button', { name: 'Cancelar reserva' }));
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button', { name: '¿Seguro? Cancelar reserva' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.getByText('Entrada cancelada')).toBeVisible();
  });
});

test('el organizador cambia de pestaña con las flechas', async ({ page, request }) => {
  const event = await publishedEvent(request);
  const ana = await signUp(request, 'Ana');
  await book(request, ana, event.general);

  await page.goto('/login');
  await page.getByLabel('Email').fill(event.owner.email);
  await page.getByLabel('Contraseña', { exact: true }).fill(PASSWORD);
  await page.keyboard.press('Enter');
  await expect(page).not.toHaveURL(/\/login/);
  await page.goto(`/org/${event.org}/events/${event.id}`);

  await tabTo(page, page.getByRole('tab', { name: 'Datos' }));
  await page.keyboard.press('End'); // Material tabs: arrows, Home and End move between tabs
  await page.keyboard.press('Enter');
  await expect(page.getByRole('tab', { name: 'Stats' })).toHaveAttribute('aria-selected', 'true');
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('tab', { name: 'Asistentes' })).toHaveAttribute(
    'aria-selected',
    'true',
  );
  await expect(page.getByText(ana.email)).toBeVisible();
});
