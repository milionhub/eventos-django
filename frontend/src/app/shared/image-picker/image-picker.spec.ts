import { ComponentFixture, TestBed } from '@angular/core/testing';
import { vi } from 'vitest';

import { ImagePicker } from './image-picker';

describe('ImagePicker', () => {
  let fixture: ComponentFixture<ImagePicker>;
  let previews: string[];
  const createObjectURL = vi.fn(() => 'blob:local');
  const revokeObjectURL = vi.fn();

  beforeEach(async () => {
    Object.assign(URL, { createObjectURL, revokeObjectURL }); // jsdom has no object URLs
    createObjectURL.mockClear();
    await TestBed.configureTestingModule({ imports: [ImagePicker] }).compileComponents();
    fixture = TestBed.createComponent(ImagePicker);
    previews = [];
    fixture.componentInstance.preview.subscribe((url) => previews.push(url));
  });

  const element = () => fixture.nativeElement as HTMLElement;

  async function pick(file: File): Promise<void> {
    const input = element().querySelector<HTMLInputElement>('input[type="file"]')!;
    Object.defineProperty(input, 'files', { value: [file], configurable: true });
    input.dispatchEvent(new Event('change'));
    await fixture.whenStable();
  }

  const file = (type: string, size = 1000) => new File([new Uint8Array(size)], 'cartel', { type });

  it('starts as a drop zone and keeps the image by default', async () => {
    await fixture.whenStable();

    expect(element().querySelector('.dropzone')?.textContent).toContain('Arrastra una imagen');
    expect(await fixture.componentInstance.change()).toEqual({ kind: 'keep' });
  });

  it('previews a picked image and offers the framing control', async () => {
    await pick(file('image/png'));

    expect(element().querySelector('.frame img')?.getAttribute('src')).toBe('blob:local');
    expect(element().querySelector('input[type="range"]')).toBeTruthy();
    expect(previews.at(-1)).toBe('blob:local');
    expect(fixture.componentInstance.hasChanges()).toBe(true);
  });

  it('rejects other formats before uploading anything', async () => {
    await pick(file('image/gif'));

    expect(element().querySelector('[role="alert"]')?.textContent).toContain('JPG, PNG o WebP');
    expect(createObjectURL).not.toHaveBeenCalled();
  });

  it('rejects files over 5 MB', async () => {
    await pick(file('image/jpeg', 5 * 1024 * 1024 + 1));

    expect(element().querySelector('[role="alert"]')?.textContent).toContain('5 MB');
  });

  it('removing the saved image asks the form to delete it', async () => {
    fixture.componentRef.setInput('currentUrl', '/media/events/a.webp');
    await fixture.whenStable();
    expect(element().querySelector('.frame img')?.getAttribute('src')).toBe('/media/events/a.webp');

    [...element().querySelectorAll<HTMLButtonElement>('button')]
      .find((b) => b.textContent?.includes('Quitar'))!
      .click();
    await fixture.whenStable();

    expect(element().querySelector('.dropzone')).toBeTruthy();
    expect(await fixture.componentInstance.change()).toEqual({ kind: 'remove' });
  });
});
