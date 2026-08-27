export const CHAT_MEMORY_EVAL_DEFAULT_ROUNDS = 3;
export const CHAT_MEMORY_EVAL_DEFAULT_JUDGE_ENABLED = true;

export type ChatMemoryEvaluationSetup = {
  model: string;
  promptKey: string;
  personaKey: string;
  embedding: string;
  timeoutSeconds: string;
  retryCount: string;
};

/** Builds the cross-feature URL contract without depending on Test Center internals. */
export function buildChatMemoryEvaluationHref(setup: ChatMemoryEvaluationSetup): string {
  const params = new URLSearchParams({
    runType: "chat_memory_eval",
    model: setup.model,
    promptKey: setup.promptKey,
    personaKey: setup.personaKey,
    embedding: setup.embedding,
    timeoutSeconds: setup.timeoutSeconds,
    retryCount: setup.retryCount,
    rounds: String(CHAT_MEMORY_EVAL_DEFAULT_ROUNDS),
    judgeEnabled: String(CHAT_MEMORY_EVAL_DEFAULT_JUDGE_ENABLED),
  });
  return `/test-center?${params.toString()}`;
}
