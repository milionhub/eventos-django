import { TestBed } from '@angular/core/testing';

import { EventThumb } from './event-thumb';

describe('EventThumb', () => {
  async function render(imageUrl: string): Promise<HTMLElement> {
    const fixture = TestBed.createComponent(EventThumb);
    fixture.componentRef.setInput('date', '2026-11-18T19:00:00Z');
    fixture.componentRef.setInput('imageUrl', imageUrl);
    await fixture.whenStable();
    return fixture.nativeElement.querySelector('.thumb');
  }

  it('shows the event image with the date on top', async () => {
    const thumb = await render('/media/events/a.webp');

    expect(thumb.style.backgroundImage).toContain('/media/events/a.webp');
    expect(thumb.querySelector('time')?.textContent).toContain('18');
  });

  it('falls back to the brand poster without an image', async () => {
    const thumb = await render('');

    expect(thumb.style.backgroundImage).toBe('');
  });
});
