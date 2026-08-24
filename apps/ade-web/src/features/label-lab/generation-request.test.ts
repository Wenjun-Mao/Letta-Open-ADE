import { describe, expect, it } from "vitest";

import { LABEL_LAB_COPY } from "./copy";
import { buildLabelGenerationRequest, type LabelGenerationForm } from "./generation-request";

const validForm: LabelGenerationForm = {
  model: "router::model",
  promptKey: "label_v1",
  schemaKey: "entities",
  maxTokens: "1024",
  timeoutSeconds: "60",
  repairRetryCount: "1",
  temperature: "0",
  topP: "1",
  topK: "20",
  articleInput: "The model should receive this unchanged.",
};

describe("buildLabelGenerationRequest", () => {
  it("keeps the valid Label Lab request payload unchanged", () => {
    expect(buildLabelGenerationRequest(validForm, LABEL_LAB_COPY.en)).toEqual({
      error: null,
      request: {
        input: "The model should receive this unchanged.",
        prompt_key: "label_v1",
        schema_key: "entities",
        model_key: "router::model",
        max_tokens: 1024,
        timeout_seconds: 60,
        repair_retry_count: 1,
        temperature: 0,
        top_p: 1,
        top_k: 20,
      },
    });
  });

  it("uses the existing error text for invalid repair retry values", () => {
    expect(buildLabelGenerationRequest({ ...validForm, repairRetryCount: "4" }, LABEL_LAB_COPY.en)).toEqual({
      request: null,
      error: LABEL_LAB_COPY.en.invalidRepairRetryCount,
    });
  });
});
