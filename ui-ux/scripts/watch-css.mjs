import fs from "node:fs";
import path from "node:path";
import { build } from "./build-css.mjs";

const root = path.resolve(import.meta.dirname, "..");
const watchRoots = [
  "src",
  "agenda",
  "bilhetes",
  "conta",
  "equipa",
  "informacao-ajuda",
  "parcerias",
  "sobre",
];
let timer;

function scheduleBuild(filename = "") {
  if (filename && !/\.(css|html)$/.test(filename)) return;
  clearTimeout(timer);
  timer = setTimeout(() => {
    console.log("\nRebuilding UI/UX styles...");
    build();
  }, 100);
}

for (const directory of watchRoots) {
  fs.watch(path.join(root, directory), { recursive: true }, (_event, filename) =>
    scheduleBuild(filename ?? ""),
  );
}
fs.watch(path.join(root, "index.html"), () => scheduleBuild("index.html"));
console.log("Watching HTML and CSS sources. Press Ctrl+C to stop.");
