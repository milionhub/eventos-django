import { TestBed } from '@angular/core/testing';

import { Meter } from './meter';

function render(value: number, max: number): HTMLElement {
  const fixture = TestBed.createComponent(Meter);
  fixture.componentRef.setInput('value', value);
  fixture.componentRef.setInput('max', max);
  fixture.componentRef.setInput('label', 'Plazas reservadas');
  fixture.detectChanges();
  return fixture.nativeElement;
}

const fill = (element: HTMLElement) => element.querySelector<HTMLElement>('.fill')!.style.width;

describe('Meter', () => {
  it('describes the ratio for screen readers', () => {
    const track = render(3, 10).querySelector('[role="meter"]')!;

    expect(track.getAttribute('aria-label')).toBe('Plazas reservadas');
    expect(track.getAttribute('aria-valuetext')).toBe('3 de 10');
  });

  it('fills in proportion and never overflows', () => {
    expect(fill(render(5, 10))).toBe('50%');
    expect(fill(render(12, 10))).toBe('100%');
  });

  it('shows a sliver for small values and nothing for zero or no limit', () => {
    expect(fill(render(1, 1000))).toBe('2%');
    expect(fill(render(0, 10))).toBe('0%');
    expect(fill(render(3, 0))).toBe('0%');
  });
});
