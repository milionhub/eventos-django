import { RoleEnum } from '../core/api/models';

export const ROLES: readonly RoleEnum[] = ['OWNER', 'MANAGER', 'STAFF'];

/** Roles that create and run events (requirements.md §4). */
export const ORGANIZERS: readonly RoleEnum[] = ['OWNER', 'MANAGER'];

export const ROLE_LABELS: Record<RoleEnum, string> = {
  OWNER: 'Propietario',
  MANAGER: 'Gestor',
  STAFF: 'Personal de acceso',
};

/** What each role can do, in words for the person choosing it (requirements.md §4). */
export const ROLE_DESCRIPTIONS: Record<RoleEnum, string> = {
  OWNER: 'Control total: equipo, organización y eventos.',
  MANAGER: 'Crea, publica y gestiona eventos.',
  STAFF: 'Valida entradas en los eventos asignados.',
};

/** Initials for an avatar: name and surname, or the first letter of the email. */
export function initials(user: { first_name: string; last_name: string; email: string }): string {
  const fromName = `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`;
  return (fromName || user.email.charAt(0)).toUpperCase();
}
