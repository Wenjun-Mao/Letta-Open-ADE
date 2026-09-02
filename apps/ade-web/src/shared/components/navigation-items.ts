export type NavigationItemKey =
  | "dashboard"
  | "agentStudio"
  | "commentLab"
  | "labelLab"
  | "schemaCenter"
  | "promptCenter"
  | "toolCenter"
  | "testCenter"
  | "apiDocs";

export type NavigationGroupKey = "build" | "content" | "evaluate" | "operations";

type NavigationItem = {
  href: string;
  key: NavigationItemKey;
};

type NavigationGroup = {
  key: NavigationGroupKey;
  items: readonly NavigationItem[];
};

export const HOME_NAVIGATION_ITEM: NavigationItem = { href: "/", key: "dashboard" };

export function buildNavigationGroups(): readonly NavigationGroup[] {
  return [
  {
    key: "build",
    items: [
      { href: "/agent-studio", key: "agentStudio" },
      { href: "/comment-lab", key: "commentLab" },
      { href: "/label-lab", key: "labelLab" },
    ],
  },
  {
    key: "content",
    items: [
      { href: "/schema-center", key: "schemaCenter" },
      { href: "/prompt-center", key: "promptCenter" },
      { href: "/tool-center", key: "toolCenter" },
    ],
  },
  {
    key: "evaluate",
    items: [{ href: "/test-center", key: "testCenter" }],
  },
  {
    key: "operations",
    items: [{ href: "/api-docs", key: "apiDocs" }],
  },
  ];
}

export const NAVIGATION_GROUPS = buildNavigationGroups();

export const ALL_NAVIGATION_ITEMS: readonly NavigationItem[] = [
  HOME_NAVIGATION_ITEM,
  ...NAVIGATION_GROUPS.flatMap((group) => group.items),
];
