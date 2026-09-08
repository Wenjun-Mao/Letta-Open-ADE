import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

import type { ModelCatalogEntry, Scenario, ScenarioOptions } from "./contracts";

export type { LabelingOutputMode, OptionEntry, SamplingDefaults, Scenario, ScenarioOptions } from "./contracts";

export function fetchOptions(
  scenario: Scenario = "chat",
  options?: { refresh?: boolean; signal?: AbortSignal },
) {
  const params = new URLSearchParams({ scenario });
  if (options?.refresh) {
    params.set("refresh", "true");
  }
  return requestJson<ScenarioOptions>(`/api/v2/model-catalog/options?${params.toString()}`, { signal: options?.signal });
}

export function fetchModelCatalog(options?: { refresh?: boolean; signal?: AbortSignal }) {
  const params = new URLSearchParams();
  if (options?.refresh) {
    params.set("refresh", "true");
  }
  const query = params.size ? `?${params.toString()}` : "";
  return requestJson<{ items: ModelCatalogEntry[] }>(`/api/v2/model-catalog/models${query}`, {
    signal: options?.signal,
  });
}
