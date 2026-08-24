export function chooseOptionKey(current: string, options: Array<{ key: string }>, fallback: string): string {
  const keys = new Set(options.map((option) => option.key.trim()).filter(Boolean));
  if (current && keys.has(current)) {
    return current;
  }
  if (fallback && keys.has(fallback)) {
    return fallback;
  }
  return options[0]?.key || current || fallback;
}
