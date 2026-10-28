import { Pipe, PipeTransform } from '@angular/core';

/**
 * Upper-cases only the first letter: "sábado 12 de diciembre" → "Sábado 12 de diciembre".
 * CSS `text-transform: capitalize` would turn it into "Sábado 12 De Diciembre".
 */
@Pipe({ name: 'capitalize' })
export class CapitalizePipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    return value ? value.charAt(0).toLocaleUpperCase('es') + value.slice(1) : '';
  }
}
