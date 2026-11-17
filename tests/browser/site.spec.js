import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const bootstrapVersion = JSON.parse(readFileSync(new URL("../../package.json", import.meta.url))).dependencies.bootstrap;

const pages = [
  ["/", "home", true],
  ["/foundation-board/", "board", true],
  ["/latest-news/", "news", false],
  ["/laws-and-regulations/", "laws", false],
  ["/affiliated-links/", "links", false],
  ["/giving-to-ntu/", "giving", true],
  ["/contact-us/", "contact", true],
  ["/404.html", "404", false],
];

async function ready(page, path) {
  await page.goto(path);
  // Pin CJK fallback for cross-machine screenshots only; production keeps the
  // visitor's existing system fallback. The site itself still self-hosts Lato.
  await page.addStyleTag({ url: "/__test-fonts/index.css" });
  await page.addStyleTag({
    content: 'body,p,h1,h2,h3,h4,h5,h6,.h1,.h2,.h3,.h4,.h5,.h6{font-family:"Lato","Noto Sans TC Variable",sans-serif!important}',
  });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => image.decode()));
  });
}

test.beforeEach(async ({ page }) => {
  await page.route("**/*", route => {
    const url = new URL(route.request().url());
    if (url.protocol === "data:" || url.hostname === "127.0.0.1") return route.continue();
    return route.abort("blockedbyclient");
  });
});

for (const [path, name, screenshot] of pages) {
  test(`${name}: content, local assets, and layout`, async ({ page }) => {
    const errors = [];
    const external = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", request => {
      if (!request.url().startsWith("http://127.0.0.1:")) external.push(request.url());
    });
    await ready(page, path);
    await expect(page.locator("html")).toHaveAttribute("lang", "zh-Hant");
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("h1")).not.toBeEmpty();
    expect(await page.evaluate(() => window.jQuery)).toBeUndefined();
    expect(await page.evaluate(() => window.bootstrap.Collapse.VERSION)).toBe(bootstrapVersion);
    expect(await page.evaluate(() => document.fonts.check("16px Lato"))).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(page.viewportSize().width);
    expect(errors).toEqual([]);
    expect(external).toEqual([]);
    await expect(page.locator("footer")).toHaveCSS("background-color", "rgb(237, 246, 245)");
    if (screenshot) await expect(page).toHaveScreenshot(`${name}.png`, { fullPage: true });
  });
}

test("keyboard skip link and focus indicator", async ({ page }) => {
  await ready(page, "/contact-us/");
  await page.keyboard.press("Tab");
  const skip = page.locator(".skip-link");
  await expect(skip).toBeFocused();
  await expect(skip).toHaveCSS("outline-style", "solid");
  await expect(skip).toHaveCSS("outline-width", "3px");
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("navigation opens, closes, and follows links without jQuery", async ({ page }) => {
  await ready(page, "/");
  const toggle = page.locator(".navbar-toggler");
  const navigation = page.locator("#navigation");
  if (page.viewportSize().width < 992) {
    await expect(navigation).toBeHidden();
    await toggle.focus();
    await page.keyboard.press("Enter");
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(navigation).toBeVisible();
    await expect(page).toHaveScreenshot("menu-open.png", { fullPage: true });
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(navigation).toBeHidden();
    await toggle.click();
    await expect(navigation).toBeVisible();
  } else {
    await expect(toggle).toBeHidden();
    await expect(navigation).toBeVisible();
  }
  await navigation.getByRole("link", { name: "聯絡我們", exact: true }).click();
  await expect(page).toHaveURL(/\/contact-us\/$/);
  await expect(page.locator("h1")).toContainText("Contact Us");
});

test("email links remain functional", async ({ page }) => {
  await ready(page, "/contact-us/");
  const addresses = page.locator("a.address");
  await expect(addresses).toHaveCount(9);
  for (const address of await addresses.all()) {
    await expect(address).toHaveAttribute("href", /^mailto:[^@]+@[^@]+$/);
    await expect(address).not.toBeEmpty();
  }
});

test("Bootstrap 4 container widths and spacing are preserved", async ({ page }) => {
  for (const width of [320, 768, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await ready(page, "/");
    const container = await page.locator("header > .container").boundingBox();
    const expected = width >= 1200 ? 1140 : width >= 768 ? 720 : width;
    expect(Math.abs(container.width - expected)).toBeLessThanOrEqual(1);
    await expect(page.locator("main .section")).toHaveCSS("padding-top", "70px");
    await expect(page.locator("footer")).toHaveCSS("padding-top", "40px");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  }
});
