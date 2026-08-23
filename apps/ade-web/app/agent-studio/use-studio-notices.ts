"use client";

import { useState } from "react";

import { toErrorMessage } from "./formatters";

export function useStudioNotices() {
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  return {
    error,
    status,
    setError,
    setStatus,
    clearError: () => setError(""),
    clear: () => {
      setError("");
      setStatus("");
    },
    reportError: (errorValue: unknown) => setError(toErrorMessage(errorValue)),
  };
}
