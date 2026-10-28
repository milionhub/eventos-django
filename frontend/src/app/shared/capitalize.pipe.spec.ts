import { CapitalizePipe } from './capitalize.pipe';

describe('CapitalizePipe', () => {
  const pipe = new CapitalizePipe();

  it('upper-cases only the first letter', () => {
    expect(pipe.transform('sábado 12 de diciembre de 2026')).toBe('Sábado 12 de diciembre de 2026');
  });

  it('handles empty values', () => {
    expect(pipe.transform(null)).toBe('');
    expect(pipe.transform('')).toBe('');
  });
});
