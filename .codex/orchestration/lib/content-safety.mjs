import { CliError } from "./core.mjs";

const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /\b(?:sk|rk|pk)-[A-Za-z0-9_-]{16,}\b/,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b/,
  /\b(?:client_secret|access_token|password)\s*[:=]\s*\S{8,}/i,
];
const RAW_CONTENT_PREFIX = /^\s*(?:```|\$\s|(?:stdout|stderr|console|transcript|traceback|stack\s*trace)\s*[:>])/i;
const EMAIL_PATTERN = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i;
const PHONE_PATTERN = /(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{2,4}\)?[ .-]?)?\d{3}[ .-]\d{4}\b/;
const APPLICATION_IDENTIFIER_PATTERN = /\b(?:app(?:lication)?[_ -]?id|client[_ -]?(?:id|key)|account[_ -]?id|game[_ -]?id)\s*[:=]\s*\S+/i;

export function assertSafeContent(owner, field, value) {
  for (const pattern of SECRET_PATTERNS) {
    if (pattern.test(value)) throw new CliError(`${owner} ${field} contains secret-like material`);
  }
  if (RAW_CONTENT_PREFIX.test(value)) {
    throw new CliError(`${owner} ${field} contains raw log or transcript content`);
  }
  if (EMAIL_PATTERN.test(value) || PHONE_PATTERN.test(value)) {
    throw new CliError(`${owner} ${field} contains user identity-like content`);
  }
  if (APPLICATION_IDENTIFIER_PATTERN.test(value)) {
    throw new CliError(`${owner} ${field} contains an application or account identifier`);
  }
}
