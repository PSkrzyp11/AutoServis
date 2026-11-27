import { mkdir, readFile, writeFile } from "node:fs/promises";

import openapiTS, { astToString } from "openapi-typescript";
import ts from "typescript";

const contractUrl = new URL("../../backend/openapi.json", import.meta.url);
const outputUrl = new URL("../src/lib/api/schema.ts", import.meta.url);

const contract = JSON.parse(await readFile(contractUrl, "utf-8"));
const generatedSource = astToString(await openapiTS(contract));
const sourceFile = ts.createSourceFile(
  "schema.ts",
  generatedSource,
  ts.ScriptTarget.Latest,
  false,
  ts.ScriptKind.TS,
);
const printer = ts.createPrinter({ removeComments: true, newLine: ts.NewLineKind.LineFeed });

await mkdir(new URL(".", outputUrl), { recursive: true });
await writeFile(outputUrl, printer.printFile(sourceFile), "utf-8");
