// Loopback-only static server. Test fonts are never added to the production site.
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";

const root = resolve(process.env.SITE_DIRECTORY || "public");
const fonts = resolve("node_modules/@fontsource-variable/noto-sans-tc");
const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript",
  ".woff2": "font/woff2",
  ".webp": "image/webp",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".png": "image/png",
  ".pdf": "application/pdf",
};

createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    const testFont = pathname.startsWith("/__test-fonts/");
    const directory = testFont ? fonts : root;
    const relative = testFont ? pathname.slice("/__test-fonts".length) : pathname;
    let filename = resolve(directory, `.${relative}`);
    if (filename !== directory && !filename.startsWith(directory + sep)) {
      response.writeHead(403).end();
      return;
    }
    if ((await stat(filename)).isDirectory()) filename = resolve(filename, "index.html");
    const content = await readFile(filename);
    response.writeHead(200, { "Content-Type": types[extname(filename)] || "application/octet-stream" });
    response.end(content);
  } catch {
    response.writeHead(404).end("Not found");
  }
}).listen(Number(process.env.PORT || 4173), "127.0.0.1");
