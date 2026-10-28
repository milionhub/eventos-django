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

  async function render(): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(Shell);
    await fixture.whenStable();
    return fixture.nativeElement;
  }

  it('renders the brand linking to home', async () => {
    const brand = (await render()).querySelector('a.brand');

    expect(brand?.textContent).toContain('#4events');
    expect(brand?.getAttribute('href')).toBe('/');
  });

  it('renders a main landmark for the routed content', async () => {
    expect((await render()).querySelector('main router-outlet')).toBeTruthy();
  });

  it('toggles the theme from the header', async () => {
    const fixture = TestBed.createComponent(Shell);
    await fixture.whenStable();
    const toggle = (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>(
      'button.theme-toggle',
    )!;
    const before = toggle.getAttribute('aria-label');

    toggle.click();
    await fixture.whenStable();

    expect(toggle.getAttribute('aria-label')).not.toBe(before);
  });
});
