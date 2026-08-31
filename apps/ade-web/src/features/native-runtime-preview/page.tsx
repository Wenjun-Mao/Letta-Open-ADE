"use client";

import { useI18n } from "@/shared/i18n";

import { NATIVE_PREVIEW_ENABLED } from "./api";
import { NativeRuntimePreviewView } from "./native-runtime-preview-view";
import { useNativeRuntimePreview } from "./use-native-runtime-preview";

export default function NativeRuntimePreviewPage() {
  const { locale } = useI18n();
  const t = (english: string, chinese: string) => (locale === "zh" ? chinese : english);
  const controller = useNativeRuntimePreview(NATIVE_PREVIEW_ENABLED);

  return (
    <NativeRuntimePreviewView
      enabled={NATIVE_PREVIEW_ENABLED}
      controller={controller}
      t={t}
    />
  );
}
