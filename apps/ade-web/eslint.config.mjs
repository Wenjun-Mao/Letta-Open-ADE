import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,
  {
    // ADE intentionally hydrates API-backed forms after mount and option changes.
    rules: { "react-hooks/set-state-in-effect": "off" },
  },
  globalIgnores([".next/**", "node_modules/**"]),
]);
