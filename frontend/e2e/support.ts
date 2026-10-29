import { APIRequestContext, expect, Page } from '@playwright/test';

export const PASSWORD = 'Taquilla-Verde-77';

let counter = 0;
/** Unique per test run, worker and call: tests run in parallel against one database. */
export function unique(name: string): string {
  return `${name}-${Date.now().toString(36)}-${process.pid}-${counter++}`;
}

export interface Person {
  email: string;
  firstName: string;
  access: string;
}

// --- Setup through the API: what a journey needs but does not test --------------------------

async function call<T>(
  request: APIRequestContext,
  method: 'get' | 'post',
  path: string,
  access?: string,
  data?: object,
): Promise<T> {
  const response = await request[method](`/api/v1/${path}`, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
    data,
  });
  expect(response.ok(), `${method.toUpperCase()} ${path}: ${await response.text()}`).toBe(true);
  return (await response.json()) as T;
}

export async function signUp(request: APIRequestContext, firstName: string): Promise<Person> {
  const email = `${unique(firstName.toLowerCase())}@e2e.test`;
  await call(request, 'post', 'auth/register/', undefined, {
    email,
    password: PASSWORD,
    first_name: firstName,
    last_name: 'Prueba',
  });
  const { access } = await call<{ access: string }>(request, 'post', 'auth/login/', undefined, {
    email,
    password: PASSWORD,
  });
  return { email, firstName, access };
}

const hoursFromNow = (hours: number) => new Date(Date.now() + hours * 3_600_000).toISOString();

export interface PublishedEvent {
  owner: Person;
  org: string;
  id: number;
  slug: string;
  title: string;
  general: number;
}

/** A published event with a "General" category. Starts in 2.5 h: still cancellable, door open. */
export async function publishedEvent(request: APIRequestContext): Promise<PublishedEvent> {
  const owner = await signUp(request, 'Olga');
  const { organization } = await call<{ organization: { slug: string } }>(
    request,
    'post',
    'organizations/',
    owner.access,
    { name: unique('Sala') },
  );
  const title = unique('Concierto');
  const base = `organizations/${organization.slug}/events/`;
  const event = await call<{ id: number; slug: string }>(request, 'post', base, owner.access, {
    title,
    description: '',
    location: 'Calle Mayor 1, Madrid',
    start_at: hoursFromNow(2.5),
    end_at: hoursFromNow(5),
    capacity: 20,
  });
  const general = await call<{ id: number }>(
    request,
    'post',
    `${base}${event.id}/ticket-types/`,
    owner.access,
    { name: 'General', description: '', capacity: 20 },
  );
  await call(request, 'post', `${base}${event.id}/publish/`, owner.access);
  return {
    owner,
    org: organization.slug,
    id: event.id,
    slug: event.slug,
    title,
    general: general.id,
  };
}

export async function book(request: APIRequestContext, person: Person, ticketType: number) {
  return call<{ id: string }>(request, 'post', 'reservations/', person.access, {
    ticket_type: ticketType,
  });
}

export async function myTickets(request: APIRequestContext, person: Person) {
  return call<{ id: string; status: string }[]>(request, 'get', 'me/tickets/', person.access);
}

export async function ticketToken(request: APIRequestContext, person: Person, ticketId: string) {
  return (await call<{ token: string }>(request, 'get', `me/tickets/${ticketId}/`, person.access))
    .token;
}

export async function addStaff(request: APIRequestContext, event: PublishedEvent, staff: Person) {
  const member = await call<{ user: { id: number } }>(
    request,
    'post',
    `organizations/${event.org}/members/`,
    event.owner.access,
    { email: staff.email, role: 'STAFF' },
  );
  await call(
    request,
    'post',
    `organizations/${event.org}/events/${event.id}/staff/`,
    event.owner.access,
    { user: member.user.id },
  );
}

// --- Through the UI ------------------------------------------------------------------------

export async function logIn(page: Page, person: Person, returnUrl = '/') {
  await page.goto(`/login?returnUrl=${encodeURIComponent(returnUrl)}`);
  await page.getByLabel('Email').fill(person.email);
  await page.getByLabel('Contraseña', { exact: true }).fill(PASSWORD);
  await page.locator('form').getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login/);
}
