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
