import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const minify = process.argv.includes("--minify");
const modules = ["core.css", "auth.css", "checkout.css"];
modules.push("states.css", "account-actions.css");
modules.push("motion.css");

export function build() {
  const temporaryDirectory = fs.mkdtempSync(
    path.join(os.tmpdir(), "enei-tailwind-"),
  );
  const entryPath = path.join(temporaryDirectory, "entry.css");
  const outputPath = path.join(root, "styles.css");
  const source = [
    "@tailwind base;",
    "@tailwind components;",
    "@tailwind utilities;",
    ...modules.map((name) =>
      fs.readFileSync(path.join(root, "src", name), "utf8"),
    ),
  ].join("\n\n");

  fs.writeFileSync(entryPath, source, "utf8");
  const tailwindCli = path.join(
    root,
    "node_modules",
    "tailwindcss",
    "lib",
    "cli.js",
  );
  const args = [
    tailwindCli,
    "-c",
    "tailwind.config.js",
    "-i",
    entryPath,
    "-o",
    outputPath,
  ];
  if (minify) args.push("--minify");

  const result = spawnSync(process.execPath, args, {
    cwd: root,
    stdio: "inherit",
  });
  fs.rmSync(temporaryDirectory, { recursive: true, force: true });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);

  if (!minify) {
    const prettierCli = path.join(
      root,
      "node_modules",
      "prettier",
      "bin",
      "prettier.cjs",
    );
    const formatted = spawnSync(
      process.execPath,
      [prettierCli, "--write", "styles.css"],
      {
        cwd: root,
        stdio: "inherit",
      },
    );
    if (formatted.error) throw formatted.error;
    if (formatted.status !== 0) process.exit(formatted.status ?? 1);
  }
}

build();
