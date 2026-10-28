import { MyTicket, TicketStatusEnum } from '../core/api/models';

export const TICKET_STATUS_LABELS: Record<TicketStatusEnum, string> = {
  VALID: 'Válida',
  USED: 'Utilizada',
  CANCELLED: 'Cancelada',
};

/** Still to be used: valid and its event has not ended. The rest goes to the history. */
export function isUpcoming(ticket: MyTicket, now = Date.now()): boolean {
  return ticket.status === 'VALID' && new Date(ticket.event.end_at).getTime() > now;
}
