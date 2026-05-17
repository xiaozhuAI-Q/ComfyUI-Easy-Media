import { $ } from "bun";
import path from "path";
import fs from "fs";

const watch = Bun.argv.includes("--watch");
const isRelease = Bun.argv.includes("--release");
const mode = isRelease ? "release" : "dev";

const rootDir = path.resolve(import.meta.dir, "..");
const outdir = path.join(rootDir, "dist", mode);
const project_name = path.basename(rootDir);

fs.mkdirSync(outdir, { recursive: true });

async function buildJS() {
  // Clear stale chunks from previous builds before writing new ones
  const chunksDir = path.join(outdir, "chunks");
  fs.rmSync(chunksDir, { recursive: true, force: true });

  const result = await Bun.build({
    entrypoints: ["./src/index.ts"],
    outdir,
    naming: {
      chunk: "chunks/[name]-[hash].[ext]",
      entry: "[name].[ext]",
      asset: "assets/[name].[ext]",
    },
    splitting: true,
    target: "browser",
    minify: isRelease,
    define: {
      "process.env.NODE_ENV": isRelease ? '"production"' : '"development"',
      "import.meta.env.PROJECT_NAME": `"${project_name}"`,
    },
    css: false,
  });

  if (!result.success) {
    for (const log of result.logs) {
      console.error(log);
    }
    throw new Error("JS build failed");
  }
  return result;
}

async function buildCSS() {
  const cssOut = path.join(outdir, "globals.css");
  const minifyFlag = isRelease ? "--minify" : "";
  await $`./node_modules/.bin/tailwindcss -i ./src/styles/globals.css -o ${cssOut} ${minifyFlag}`;
  // Replace __CUSTOM_NODE_CLASS__ placeholder with the lowercased project name.
  const widgetClass = project_name.toLowerCase();
  const css = fs.readFileSync(cssOut, "utf-8");
  fs.writeFileSync(cssOut, css.replaceAll("__CUSTOM_NODE_CLASS__", widgetClass));
}

type BuildType = "all" | "js" | "css";

async function build(type: BuildType = "all") {
  const start = Date.now();
  try {
    if (type === "all" || type === "css") await buildCSS();
    if (type === "all" || type === "js") {
      const result = await buildJS();
      console.log(
        `[build:${mode}] Done in ${Date.now() - start}ms (${result.outputs.length} JS output(s))`,
      );
    }
  } catch (e) {
    console.error(`[build:${mode}] Error:`, e);
  }
}

if (watch) {
  await build("all");

  const DEBOUNCE = 150;
  let jsTimer: ReturnType<typeof setTimeout> | null = null;
  let cssTimer: ReturnType<typeof setTimeout> | null = null;

  const watcher = fs.watch("./src", { recursive: true }, (_event, filename) => {
    if (!filename) return;
    const isCss = filename.endsWith(".css");

    if (isCss) {
      if (cssTimer) clearTimeout(cssTimer);
      cssTimer = setTimeout(() => {
        console.log(`[build:watch] ${filename} changed, rebuilding CSS...`);
        void build("css");
      }, DEBOUNCE);
    } else {
      if (jsTimer) clearTimeout(jsTimer);
      jsTimer = setTimeout(() => {
        console.log(`[build:watch] ${filename} changed, rebuilding JS...`);
        void build("js");
      }, DEBOUNCE);
    }
  });

  console.log("[build:watch] Watching src/ for changes...");
  process.on("SIGINT", () => {
    watcher.close();
    process.exit(0);
  });

  // Keep the process alive
  await new Promise(() => {});
} else {
  await build("all");
}
