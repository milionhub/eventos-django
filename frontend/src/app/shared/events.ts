import { EventStatusEnum } from '../core/api/models';

export const EVENT_STATUS_LABELS: Record<EventStatusEnum, string> = {
  DRAFT: 'Borrador',
  PUBLISHED: 'Publicado',
  CANCELLED: 'Cancelado',
};

/** Label for an organizer, where "finished" is computed (RN-08), not a stored status. */
export function eventStatusLabel(event: { status: EventStatusEnum; is_finished: boolean }) {
  return event.is_finished ? 'Finalizado' : EVENT_STATUS_LABELS[event.status];
}

const pad = (n: number) => String(n).padStart(2, '0');

/** ISO instant from the API → value for `<input type="datetime-local">` in local time. */
export function toLocalInput(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** `datetime-local` value (local time, no zone) → ISO instant in UTC for the API. */
export function fromLocalInput(value: string): string {
  return new Date(value).toISOString();
}
