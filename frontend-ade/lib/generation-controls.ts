import type { OptionEntry } from "./api";

export type SamplingScenario = "agent_studio" | "comment_lab" | "label_lab";
export type SamplingField = "temperature" | "top_p" | "top_k";

function parseFiniteNumber(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function parseNonNegativeInteger(value: string): number | null {
  const parsed = parseFiniteNumber(value);
  return parsed !== null && Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

export function parseIntegerInRange(value: string, minimum: number, maximum: number): number | null {
  const parsed = parseFiniteNumber(value);
  return parsed !== null
    && Number.isInteger(parsed)
    && parsed >= minimum
    && parsed <= maximum
    ? parsed
    : null;
}

export function parsePositiveNumber(value: string): number | null {
  const parsed = parseFiniteNumber(value);
  return parsed !== null && parsed > 0 ? parsed : null;
}

export function parseTemperature(value: string): number | null {
  const parsed = parseFiniteNumber(value);
  return parsed !== null && parsed >= 0 && parsed <= 2 ? parsed : null;
}

export function parseTopP(value: string): number | null {
  const parsed = parseFiniteNumber(value);
  return parsed !== null && parsed > 0 && parsed <= 1 ? parsed : null;
}

export function parseOptionalTemperature(value: string): number | undefined | null {
  return value.trim() ? parseTemperature(value) : undefined;
}

export function parseOptionalTopP(value: string): number | undefined | null {
  return value.trim() ? parseTopP(value) : undefined;
}

export function parseOptionalPositiveInteger(value: string): number | undefined | null {
  if (!value.trim()) {
    return undefined;
  }
  const parsed = parseFiniteNumber(value);
  return parsed !== null && Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function samplingDefaultString(
  option: OptionEntry | null | undefined,
  scenario: SamplingScenario,
  field: SamplingField,
): string | null {
  const scenarioDefaults = option?.scenario_sampling_defaults?.[scenario];
  const value = scenarioDefaults?.[field] ?? option?.sampling_defaults?.[field];
  return value === undefined || value === null ? null : String(value);
}

export function formatModelOptionLabel(option: OptionEntry, unavailableSuffix = ""): string {
  const key = (option.provider_model_id || option.key || "").trim();
  const label = (option.label || "").trim();
  const sourceLabel = (option.source_label || "").trim();
  const base = label && label !== key ? `${label} (${key})` : key;
  const withSource = sourceLabel ? `${base} - ${sourceLabel}` : base;
  return option.available === false ? `${withSource}${unavailableSuffix}` : withSource;
}
