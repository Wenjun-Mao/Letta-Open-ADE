import { redirect } from "next/navigation";

type LegacyRouteProps = { searchParams: Record<string, string | string[] | undefined> };

function queryString(searchParams: LegacyRouteProps["searchParams"]): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    for (const entry of Array.isArray(value) ? value : [value]) {
      if (entry !== undefined) {
        params.append(key, entry);
      }
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export default function PromptPersonaLabPage({ searchParams }: LegacyRouteProps) {
  redirect(`/prompt-center${queryString(searchParams)}`);
}
