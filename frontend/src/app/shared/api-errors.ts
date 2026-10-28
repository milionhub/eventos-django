import { HttpErrorResponse } from '@angular/common/http';

/**
 * Text to show the user for a failed API call. Business errors come back as
 * `{code, detail}` with a message already written for them (apps.core.exceptions).
 */
export function errorText(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.error?.code && error.error?.detail) return error.error.detail;
    if (error.status === 403 || error.status === 404) {
      return 'Ya no tienes permiso para hacer esto o el elemento ya no existe.';
    }
  }
  return 'No se ha podido completar la acción. Inténtalo de nuevo.';
}
