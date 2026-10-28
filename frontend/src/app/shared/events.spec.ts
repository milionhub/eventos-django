import { eventStatusLabel, fromLocalInput, toLocalInput } from './events';

describe('event helpers', () => {
  it('converts between API instants and datetime-local values without drifting', () => {
    const local = '2026-11-20T19:30';

    const iso = fromLocalInput(local);

    expect(iso.endsWith('Z')).toBe(true); // always UTC for the API
    expect(toLocalInput(iso)).toBe(local);
  });

  it('labels finished events as such, whatever their stored status', () => {
    expect(eventStatusLabel({ status: 'PUBLISHED', is_finished: true })).toBe('Finalizado');
    expect(eventStatusLabel({ status: 'DRAFT', is_finished: false })).toBe('Borrador');
  });
});
