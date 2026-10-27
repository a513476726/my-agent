import { execFileSync } from "node:child_process";
import {
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const expectedRoot = process.env.EXPECTED_GENERATED_DIR
  ? resolve(process.env.EXPECTED_GENERATED_DIR)
  : join(packageRoot, "src", "generated");
const bin = join(
  packageRoot,
  "node_modules",
  ".bin",
  process.platform === "win32" ? "openapi-ts.cmd" : "openapi-ts",
);

function listFiles(directory, root = directory) {
  return readdirSync(directory)
    .flatMap((name) => {
      const path = join(directory, name);
      return statSync(path).isDirectory() ? listFiles(path, root) : [relative(root, path)];
    })
    .sort();
}

const tempRoot = mkdtempSync(join(tmpdir(), "my-agent-contracts-"));
try {
  execFileSync(
    bin,
    ["-i", "openapi.json", "-o", tempRoot, "-c", "@hey-api/client-fetch", "-s"],
    { cwd: packageRoot, stdio: "inherit" },
  );

  const expectedFiles = listFiles(expectedRoot);
  const actualFiles = listFiles(tempRoot);
  const missing = expectedFiles.filter((file) => !actualFiles.includes(file));
  const extra = actualFiles.filter((file) => !expectedFiles.includes(file));
  const changed = expectedFiles.filter((file) => {
    if (!actualFiles.includes(file)) return false;
    return !readFileSync(join(expectedRoot, file)).equals(readFileSync(join(tempRoot, file)));
  });

  if (missing.length > 0 || extra.length > 0 || changed.length > 0) {
    console.error("共享类型生成产物与 openapi.json 不一致，请运行 pnpm --filter @my-agent/shared-types generate");
    for (const file of missing) console.error(`  缺失：${file}`);
    for (const file of extra) console.error(`  多余：${file}`);
    for (const file of changed) console.error(`  过期：${file}`);
    process.exitCode = 1;
  } else {
    console.log("共享类型生成产物与 openapi.json 一致");
  }
} finally {
  rmSync(tempRoot, { recursive: true, force: true });
}
