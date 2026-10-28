import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EventDetail, EventWriteRequest } from '../../../core/api/models';
import { toLocalInput } from '../../../shared/events';
import { EventForm } from './event-form';

const EVENT: EventDetail = {
  id: 1,
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
  publish_blockers: [],
};

describe('EventForm', () => {
  let fixture: ComponentFixture<EventForm>;
  let saved: EventWriteRequest[];

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [EventForm] }).compileComponents();
    fixture = TestBed.createComponent(EventForm);
    saved = [];
    fixture.componentInstance.save.subscribe((value) => saved.push(value));
  });

  const element = () => fixture.nativeElement as HTMLElement;
  const input = (name: string) =>
    element().querySelector<HTMLInputElement>(`[formcontrolname="${name}"]`)!;
  const submit = async () => {
    element().querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  };

  it('fills in an existing event in local time', async () => {
    fixture.componentRef.setInput('event', EVENT);
    await fixture.whenStable();

    expect(input('title').value).toBe('Jazz en Apolo');
    expect(input('start_at').value).toBe(toLocalInput(EVENT.start_at));
  });

  it('emits UTC instants for the API', async () => {
    fixture.componentRef.setInput('event', EVENT);
    await fixture.whenStable();

    await submit();

    expect(saved).toHaveLength(1);
    expect(saved[0].start_at).toBe('2026-11-20T18:30:00.000Z');
    expect(saved[0].capacity).toBe(300);
  });

  it('does not emit when the end is before the start', async () => {
    fixture.componentRef.setInput('event', EVENT);
    await fixture.whenStable();
    input('end_at').value = toLocalInput('2026-11-20T17:00:00Z');
    input('end_at').dispatchEvent(new Event('input'));

    await submit();

    expect(saved).toHaveLength(0);
    expect(element().textContent).toContain('El fin debe ser posterior al inicio.');
  });

  it('shows how long the event lasts', async () => {
    fixture.componentRef.setInput('event', EVENT);
    await fixture.whenStable();

    expect(element().textContent).toContain('Dura 3 h');
  });

  it('streams what is typed for the live preview', async () => {
    const changes: unknown[] = [];
    fixture.componentInstance.changes.subscribe((value) => changes.push(value));
    await fixture.whenStable();

    input('title').value = 'Festival';
    input('title').dispatchEvent(new Event('input'));

    expect(changes.at(-1)).toMatchObject({ title: 'Festival' });
  });

  it('hides the button and locks the fields when read-only', async () => {
    fixture.componentRef.setInput('event', EVENT);
    fixture.componentRef.setInput('readonly', true);
    await fixture.whenStable();

    expect(element().querySelector('button[type="submit"]')).toBeNull();
    expect(input('title').disabled).toBe(true);
  });
});
