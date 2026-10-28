import { RoleEnum } from '../core/api/models';

export const ROLES: readonly RoleEnum[] = ['OWNER', 'MANAGER', 'STAFF'];

export const ROLE_LABELS: Record<RoleEnum, string> = {
  OWNER: 'Propietario',
  MANAGER: 'Gestor',
  STAFF: 'Personal de acceso',
};

/** Initials for an avatar: name and surname, or the first letter of the email. */
export function initials(user: { first_name: string; last_name: string; email: string }): string {
  const fromName = `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`;
  return (fromName || user.email.charAt(0)).toUpperCase();
}
