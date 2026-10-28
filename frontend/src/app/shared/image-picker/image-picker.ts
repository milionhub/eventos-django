import { Component, computed, effect, input, output, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

/** What happens to the image when the form is saved. */
export type ImageChange = { kind: 'keep' } | { kind: 'remove' } | { kind: 'set'; blob: Blob };

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_BYTES = 5 * 1024 * 1024; // same limit as the backend (ADR-0008)
const RATIO = 16 / 9;
const OUTPUT_WIDTH = 1600;

/**
 * Pick an image by dropping it or browsing, preview it as a 16:9 poster and choose the
 * framing. The crop happens here, in the browser; the backend validates and re-encodes
 * whatever arrives anyway.
 */
@Component({
  selector: 'app-image-picker',
  imports: [MatButtonModule, MatIconModule],
  templateUrl: './image-picker.html',
  styleUrl: './image-picker.scss',
})
export class ImagePicker {
  /** The image already saved, if any (`/media/...`). */
  readonly currentUrl = input('');
  readonly disabled = input(false);
  /** Object URL of what would be shown now, for live previews elsewhere. */
  readonly preview = output<string>();

  private readonly file = signal<File | null>(null);
  private readonly removed = signal(false);
  protected readonly localUrl = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly dragging = signal(false);

  /** 0–100 along the axis with room to move: the focus of the crop. */
  protected readonly focus = signal(50);
  /** Taller than 16:9 → we can move the crop up and down; wider → left and right. */
  protected readonly axis = signal<'vertical' | 'horizontal'>('vertical');

  protected readonly shownUrl = computed(
    () => this.localUrl() ?? (this.removed() ? '' : this.currentUrl()),
  );
  protected readonly objectPosition = computed(() =>
    this.axis() === 'vertical' ? `50% ${this.focus()}%` : `${this.focus()}% 50%`,
  );

  constructor() {
    effect((onCleanup) => {
      const file = this.file();
      if (!file) {
        this.localUrl.set(null);
        return;
      }
      const url = URL.createObjectURL(file);
      this.localUrl.set(url);
      onCleanup(() => URL.revokeObjectURL(url));
    });
    effect(() => this.preview.emit(this.shownUrl()));
  }

  /** Whether the form has something to send for the image. */
  hasChanges(): boolean {
    return this.file() !== null || this.removed();
  }

  /** What to do with the image on save; crops the new file to 16:9 if there is one. */
  async change(): Promise<ImageChange> {
    const file = this.file();
    if (file) return { kind: 'set', blob: await this.crop(file) };
    return this.removed() ? { kind: 'remove' } : { kind: 'keep' };
  }

  /** After a successful save: the new image is now the current one. */
  reset(): void {
    this.file.set(null);
    this.removed.set(false);
    this.focus.set(50);
  }

  protected choose(files: FileList | null | undefined): void {
    const file = files?.[0];
    if (!file) return;
    if (!ACCEPTED.includes(file.type)) {
      this.error.set('Solo imágenes JPG, PNG o WebP.');
      return;
    }
    if (file.size > MAX_BYTES) {
      this.error.set('La imagen no puede pesar más de 5 MB.');
      return;
    }
    this.error.set(null);
    this.removed.set(false);
    this.focus.set(50);
    this.file.set(file);
  }

  protected remove(): void {
    this.file.set(null);
    this.removed.set(!!this.currentUrl());
  }

  protected onLoad(image: HTMLImageElement): void {
    const ratio = image.naturalWidth / image.naturalHeight;
    this.axis.set(ratio > RATIO ? 'horizontal' : 'vertical');
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    if (!this.disabled()) this.choose(event.dataTransfer?.files);
  }

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
    if (!this.disabled()) this.dragging.set(true);
  }

  /** Crop to 16:9 around the chosen focus and scale down to at most 1600 px wide. */
  private async crop(file: File): Promise<Blob> {
    const bitmap = await createImageBitmap(file); // honours the photo's EXIF orientation
    let sx = 0;
    let sy = 0;
    let sw = bitmap.width;
    let sh = bitmap.height;
    if (bitmap.width / bitmap.height > RATIO) {
      sw = bitmap.height * RATIO;
      sx = ((bitmap.width - sw) * this.focus()) / 100;
    } else {
      sh = bitmap.width / RATIO;
      sy = ((bitmap.height - sh) * this.focus()) / 100;
    }
    const width = Math.round(Math.min(OUTPUT_WIDTH, sw));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = Math.round(width / RATIO);
    canvas.getContext('2d')!.drawImage(bitmap, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    return new Promise((resolve, reject) =>
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('crop'))),
        'image/jpeg',
        0.9,
      ),
    );
  }
}
