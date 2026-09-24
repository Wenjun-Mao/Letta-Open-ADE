"use client";

// Agent Studio resource archive and subject-rename commands.

import type { Dispatch, SetStateAction } from "react";

import {
  archiveAgentStudioDefinition,
  archiveAgentStudioSession,
  archiveAgentStudioSubject,
  restoreAgentStudioDefinition,
  restoreAgentStudioSession,
  restoreAgentStudioSubject,
  updateAgentStudioSubject,
} from "./api";
import type { AgentStudioSession, SubjectMemories } from "./types";

type ResourceActionDependencies = {
  session: AgentStudioSession | null;
  subjectRename: string;
  refreshWorkspace: () => Promise<void>;
  refreshSelected: (conversationId: string) => Promise<SubjectMemories | null>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string>>;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error || "Unexpected Agent Studio error.");
}

export function useResourceActions({
  session, subjectRename, refreshWorkspace, refreshSelected, setBusy, setError,
}: ResourceActionDependencies) {
  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function setSessionArchived(archived: boolean) {
    if (!session) return;
    await run(async () => {
      if (archived) await archiveAgentStudioSession(session.conversation.id);
      else await restoreAgentStudioSession(session.conversation.id);
      await Promise.all([refreshWorkspace(), refreshSelected(session.conversation.id)]);
    });
  }

  async function setDefinitionArchived(archived: boolean) {
    const rootId = session?.agent_definition.agent_definition_id;
    if (!rootId || !session) return;
    await run(async () => {
      if (archived) await archiveAgentStudioDefinition(rootId);
      else await restoreAgentStudioDefinition(rootId);
      await Promise.all([refreshWorkspace(), refreshSelected(session.conversation.id)]);
    });
  }

  async function setSubjectArchived(archived: boolean) {
    if (!session) return;
    await run(async () => {
      if (archived) await archiveAgentStudioSubject(session.memory_subject.id);
      else await restoreAgentStudioSubject(session.memory_subject.id);
      await Promise.all([refreshWorkspace(), refreshSelected(session.conversation.id)]);
    });
  }

  async function renameSubject() {
    if (!session || !subjectRename.trim() || subjectRename.trim() === session.memory_subject.display_name) return;
    await run(async () => {
      await updateAgentStudioSubject(session.memory_subject.id, {
        display_name: subjectRename.trim(),
        expected_version: session.memory_subject.version,
      });
      await Promise.all([refreshWorkspace(), refreshSelected(session.conversation.id)]);
    });
  }

  return { setSessionArchived, setDefinitionArchived, setSubjectArchived, renameSubject };
}
