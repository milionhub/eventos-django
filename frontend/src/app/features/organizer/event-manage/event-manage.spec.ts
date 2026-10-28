import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { EventDetail } from '../../../core/api/models';
import { EventManage } from './event-manage';

const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve));
const URL = '/api/v1/organizations/sala-apolo/events/7/';

const detail = (overrides: Partial<EventDetail> = {}): EventDetail => ({
  id: 7,
  title: 'Jazz en Apolo',
  slug: 'jazz-en-apolo',
  location: 'Barcelona',
  description: '',
  image_url: '',
  start_at: '2026-11-20T18:30:00Z',
  end_at: '2026-11-20T21:30:00Z',
  capacity: 300,
  status: 'DRAFT',
  is_finished: false,
  published_at: null,
  cancelled_at: null,
  created_at: '2026-10-28T10:00:00Z',
  ticket_types: [],
  allocated_capacity: 0,
  publish_blockers: ['Añade al menos una categoría de entrada.'],
  ...overrides,
});

describe('EventManage', () => {
  let fixture: ComponentFixture<EventManage>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventManage],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const element = () => fixture.nativeElement as HTMLElement;
  const button = (text: string) =>
    [...element().querySelectorAll<HTMLButtonElement>('button')].find((b) =>
      b.textContent?.includes(text),
    )!;

  async function render(event: EventDetail, tab?: string): Promise<void> {
    fixture = TestBed.createComponent(EventManage);
    fixture.componentRef.setInput('org', 'sala-apolo');
    fixture.componentRef.setInput('id', '7');
    if (tab) fixture.componentRef.setInput('tab', tab);
    fixture.detectChanges();
    await flushMicrotasks();
    http.expectOne(URL).flush(event);
    await settle();
  }

  /** Not whenStable(): after each action the component reloads the event, a request the
   * test answers explicitly, so the fixture is not "stable" until then. */
  async function settle(): Promise<void> {
    await flushMicrotasks();
    fixture.detectChanges();
    await flushMicrotasks();
  }

  it('explains what is missing and keeps Publish disabled', async () => {
    await render(detail());

    expect(element().querySelector('.blockers')?.textContent).toContain(
      'Añade al menos una categoría de entrada.',
    );
    expect(button('Publicar').disabled).toBe(true);
  });

  it('publishes a ready draft and refreshes it', async () => {
    await render(detail({ publish_blockers: [] }));

    button('Publicar').click();
    http.expectOne(`${URL}publish/`).flush(detail({ status: 'PUBLISHED' }));
    await settle();
    http.expectOne(URL).flush(detail({ status: 'PUBLISHED', publish_blockers: [] }));
    await settle();

    expect(element().querySelector('[role="status"]')?.textContent).toContain('Evento publicado');
    expect(element().textContent).toContain('Ver página pública');
  });

  it('asks before cancelling', async () => {
    await render(detail());

    button('Cancelar evento').click();
    await settle();
    http.expectNone(`${URL}cancel/`);
    expect(button('¿Seguro?')).toBeTruthy();

    button('¿Seguro?').click();
    http.expectOne(`${URL}cancel/`).flush(detail({ status: 'CANCELLED' }));
    await settle();
    http.expectOne(URL).flush(detail({ status: 'CANCELLED' }));
    await settle();

    expect(element().textContent).toContain('Este evento está cancelado');
  });

  it('shows why a category does not fit', async () => {
    await render(detail(), 'entradas');

    const name = element().querySelector<HTMLInputElement>('.add input[formcontrolname="name"]')!;
    name.value = 'Palco';
    name.dispatchEvent(new Event('input'));
    element().querySelector<HTMLFormElement>('form.add')!.dispatchEvent(new Event('submit'));

    const req = http.expectOne(`${URL}ticket-types/`);
    expect(req.request.body).toEqual({ name: 'Palco', capacity: 50, description: '' });
    req.flush(
      { code: 'capacity_exceeded', detail: 'La suma de los cupos superaría el aforo.' },
      { status: 409, statusText: 'Conflict' },
    );
    await settle();

    expect(element().querySelector('[role="alert"]')?.textContent).toContain('superaría el aforo');
  });

  it('caps a new category at the seats still unassigned', async () => {
    await render(detail({ capacity: 300, allocated_capacity: 280 }), 'entradas');

    expect(element().textContent).toContain('Quedan 20 plazas');
    button('Usar las 20 libres').click();
    await settle();
    const capacity = element().querySelector<HTMLInputElement>(
      '.add input[formcontrolname="capacity"]',
    )!;
    expect(capacity.value).toBe('20');

    capacity.value = '21';
    capacity.dispatchEvent(new Event('input'));
    capacity.dispatchEvent(new Event('blur'));
    await settle();
    expect(element().textContent).toContain('Solo quedan 20 libres.');
  });

  it('only loads staff and members when the Staff tab is opened', async () => {
    await render(detail(), 'staff');

    http.expectOne(`${URL}staff/`).flush([]);
    http.expectOne('/api/v1/organizations/sala-apolo/members/').flush([]);
    await settle();

    expect(element().textContent).toContain('Nadie asignado todavía.');
  });
});
