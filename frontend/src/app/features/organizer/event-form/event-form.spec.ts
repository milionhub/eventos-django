import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EventDetail } from '../../../core/api/models';
import { EventForm, EventFormValue } from './event-form';

const EVENT: EventDetail = {
  id: 1,
  title: 'Jazz en Apolo',
  slug: 'jazz-en-apolo',
  location: 'Barcelona',
  description: '',
  image_url: '',
  start_at: '2026-11-20T18:30:00.000Z',
  end_at: '2026-11-20T21:30:00.000Z',
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
  let saved: EventFormValue[];

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [EventForm] }).compileComponents();
    fixture = TestBed.createComponent(EventForm);
    saved = [];
    fixture.componentInstance.save.subscribe((value) => saved.push(value));
  });

  const element = () => fixture.nativeElement as HTMLElement;
  // Bracket access reaches the protected form with its real type.
  const form = () => fixture.componentInstance['form'];
  const input = (name: string) =>
    element().querySelector<HTMLInputElement>(`[formcontrolname="${name}"]`)!;

  async function submit(): Promise<void> {
    element().querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    await new Promise((resolve) => setTimeout(resolve)); // the image step is async
  }

  async function withEvent(): Promise<void> {
    fixture.componentRef.setInput('event', EVENT);
    await fixture.whenStable();
  }

  it('fills in an existing event, day and time in separate fields', async () => {
    await withEvent();

    expect(input('title').value).toBe('Jazz en Apolo');
    expect(input('startDate').value).not.toBe('');
    expect(input('startTime').value).toMatch(/\d{1,2}:30/);
    expect(element().textContent).toContain('Dura 3 h');
  });

  it('emits the start and end as UTC instants, and keeps the image by default', async () => {
    await withEvent();

    await submit();

    expect(saved).toHaveLength(1);
    expect(saved[0].data.start_at).toBe(EVENT.start_at);
    expect(saved[0].data.end_at).toBe(EVENT.end_at);
    expect(saved[0].data.capacity).toBe(300);
    expect(saved[0].image).toEqual({ kind: 'keep' });
  });

  it('keeps the chosen time when another day is picked', async () => {
    await withEvent();
    const time = form().controls.startTime.value!;

    // 24 December, keeping the hours (the end moves too, so it stays after the start).
    form().patchValue({ startDate: new Date(2026, 11, 24), endDate: new Date(2026, 11, 24) });
    await submit();

    const start = new Date(saved[0].data.start_at);
    expect([start.getMonth(), start.getDate()]).toEqual([11, 24]);
    expect([start.getHours(), start.getMinutes()]).toEqual([time.getHours(), time.getMinutes()]);
  });

  it('sets the end from a quick duration', async () => {
    await withEvent();

    [...element().querySelectorAll<HTMLButtonElement>('.quick-chip')]
      .find((b) => b.textContent?.trim() === '2 h')!
      .click();
    await fixture.whenStable();

    expect(element().textContent).toContain('Dura 2 h');
  });

  it('does not emit when the end is before the start', async () => {
    await withEvent();
    const before = new Date(new Date(EVENT.start_at).getTime() - 3600_000);
    form().patchValue({ endDate: before, endTime: before });

    await submit();

    expect(saved).toHaveLength(0);
    expect(element().textContent).toContain('El fin debe ser posterior al inicio.');
  });

  it('streams what is typed, with the start as an instant, for the live preview', async () => {
    const changes: { title: string; start_at: string }[] = [];
    fixture.componentInstance.changes.subscribe((value) => changes.push(value));
    await withEvent();

    input('title').value = 'Festival';
    input('title').dispatchEvent(new Event('input'));

    expect(changes.at(-1)).toMatchObject({ title: 'Festival', start_at: EVENT.start_at });
  });

  it('hides the button and locks the fields when read-only', async () => {
    fixture.componentRef.setInput('readonly', true);
    await withEvent();

    expect(element().querySelector('button[type="submit"]')).toBeNull();
    expect(input('title').disabled).toBe(true);
  });
});
