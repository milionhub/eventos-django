import { eventStatusLabel } from './events';

describe('event helpers', () => {
  it('labels finished events as such, whatever their stored status', () => {
    expect(eventStatusLabel({ status: 'PUBLISHED', is_finished: true })).toBe('Finalizado');
    expect(eventStatusLabel({ status: 'DRAFT', is_finished: false })).toBe('Borrador');
  });
});
