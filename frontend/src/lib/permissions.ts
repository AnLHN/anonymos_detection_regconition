import type { CurrentUser } from './types';

export function hasPermission(user: CurrentUser | null | undefined, permission: string) {
  return Boolean(user?.permissions?.includes(permission));
}
