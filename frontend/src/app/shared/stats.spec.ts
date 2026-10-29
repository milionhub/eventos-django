import { percent } from './stats';

describe('percent', () => {
  it('rounds to a whole number', () => {
    expect(percent(1, 3)).toBe(33);
    expect(percent(2, 3)).toBe(67);
  });

  it('is 0 when there is nothing to divide', () => {
    expect(percent(0, 0)).toBe(0);
    expect(percent(5, 0)).toBe(0);
  });
});
