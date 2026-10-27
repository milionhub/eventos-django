import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Shell } from './shell';

describe('Shell', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Shell],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('renders the brand linking to home', async () => {
    const fixture = TestBed.createComponent(Shell);
    await fixture.whenStable();
    const brand = (fixture.nativeElement as HTMLElement).querySelector('a.brand');

    expect(brand?.textContent).toContain('eventos');
    expect(brand?.getAttribute('href')).toBe('/');
  });

  it('renders a main landmark for the routed content', async () => {
    const fixture = TestBed.createComponent(Shell);
    await fixture.whenStable();

    expect((fixture.nativeElement as HTMLElement).querySelector('main router-outlet')).toBeTruthy();
  });
});
