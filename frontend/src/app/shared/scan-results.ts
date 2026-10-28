import { ScanResultEnum } from '../core/api/models';

/** How each scan result looks at the door (requirements.md RN-32). */
export interface ScanResultView {
  title: string;
  icon: string;
  tone: 'ok' | 'warn' | 'error';
}

export const SCAN_RESULTS: Record<ScanResultEnum, ScanResultView> = {
  VALID: { title: 'Válida', icon: 'check_circle', tone: 'ok' },
  ALREADY_USED: { title: 'Ya utilizada', icon: 'history', tone: 'warn' },
  CANCELLED: { title: 'Entrada cancelada', icon: 'block', tone: 'error' },
  NOT_FOUND: { title: 'Entrada no válida', icon: 'help', tone: 'error' },
  WRONG_EVENT: { title: 'Es de otro evento', icon: 'event_busy', tone: 'error' },
  EVENT_NOT_ACTIVE: { title: 'Fuera de horario', icon: 'schedule', tone: 'error' },
  UNAUTHORIZED: { title: 'No puedes validar aquí', icon: 'lock', tone: 'error' },
};

/** Short buzz for a valid ticket, a longer pattern for anything else. */
export const VIBRATION: Record<ScanResultView['tone'], number[]> = {
  ok: [80],
  warn: [80, 60, 80],
  error: [80, 60, 80, 60, 200],
};
