import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const noCommentsRule = {
  meta: {
    type: "suggestion",
    docs: { description: "Disallow comments, code must explain itself" },
    schema: [],
  },
  create(context) {
    return {
      Program() {
        for (const comment of context.sourceCode.getAllComments()) {
          context.report({
            loc: comment.loc,
            message: "Comments are not allowed in this repository.",
          });
        }
      },
    };
  },
};

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    plugins: { autoservis: { rules: { "no-comments": noCommentsRule } } },
    linterOptions: { noInlineConfig: true, reportUnusedDisableDirectives: "off" },
    rules: {
      "autoservis/no-comments": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "coverage/**", "next-env.d.ts"]),
]);

export default eslintConfig;
