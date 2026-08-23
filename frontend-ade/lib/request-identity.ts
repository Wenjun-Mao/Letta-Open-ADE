export type RequestIdentity = {
  resourceId: string;
  version: number;
};

export function isCurrentRequest(identity: RequestIdentity, currentResourceId: string, currentVersion: number): boolean {
  return identity.resourceId === currentResourceId && identity.version === currentVersion;
}
