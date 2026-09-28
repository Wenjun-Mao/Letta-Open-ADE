"use client";

import { useRef, type ReactNode } from "react";

export function fieldCaptionId(inputId: string): string {
  return `${inputId}-caption`;
}

export function FieldCaption({ inputId, children }: { inputId: string; children: ReactNode }) {
  const pointerStart = useRef<{ x: number; y: number } | null>(null);
  return <span id={fieldCaptionId(inputId)} className="studio-field-caption"
    onPointerDown={(event) => { pointerStart.current = { x: event.clientX, y: event.clientY }; }}
    onPointerUp={(event) => {
      const start = pointerStart.current;
      pointerStart.current = null;
      if (!start || Math.hypot(event.clientX - start.x, event.clientY - start.y) > 4) return;
      document.getElementById(inputId)?.focus();
    }}
  >{children}</span>;
}
