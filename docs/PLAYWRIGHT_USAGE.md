# Playwright usage

How to use Playwright for browser automation and visual testing in this repo.

## Install

Playwright is a dev dependency. If the repo does not already have a
`package.json`, create one first. Then install Playwright and its browsers:

```bash
npm init -y
npm install --save-dev playwright
npx playwright install
```

`npm init -y` creates a default `package.json` at the repo root. `npm install
--save-dev playwright` gets the `playwright` Node library and records it under
`devDependencies`. `npx playwright install` downloads browser binaries
(Chromium, Firefox, WebKit). If `package.json` already exists, skip
`npm init -y` and just run `npm install` (to pick up existing deps) followed
by `npx playwright install`.

### Quick install script

Repos propagated from the starter template ship `devel/setup_playwright.sh`,
which automates the install end-to-end (chromium only, idempotent):

```bash
bash devel/setup_playwright.sh
```

The script installs `@playwright/test` (the test runner) rather than the bare
`playwright` library. Use it when the repo's tests rely on the test-runner
fixtures and assertions; use the manual `npm install --save-dev playwright`
above when the scripts use the library directly (see [Packages](#packages)).

### Shared helper: `repo_root.mjs`

`tests/playwright/repo_root.mjs` is centrally propagated by
`propagate_style_guides.py`. Do not edit it per-repo. It exports `REPO_ROOT`
resolved via `git rev-parse --show-toplevel`, so test scripts can compute
absolute paths without brittle relative-path math:

```javascript
import { REPO_ROOT } from "./repo_root.mjs";
import path from "node:path";

const pagePath = path.join(REPO_ROOT, "index.html");
```

## Key rule: scripts must run from the project root

Node resolves `import 'playwright'` by searching `node_modules/` starting from the
script's own directory and walking up. A script in `/tmp/` will not find the project's
`node_modules/`.

**Wrong:**

```bash
node /tmp/_test_game_ui.mjs
# Error: Cannot find module 'playwright'
```

**Right:**

```bash
cd /Users/vosslab/nsh/cell-culture-game-claude
node tests/playwright/test_game_ui.mjs
```

Put Playwright scripts in `tests/playwright/`.

## Script location

Store Playwright scripts in `tests/playwright/` with an `.mjs` extension, for example
`tests/playwright/test_game_ui.mjs`. Helpers (`tests/playwright/helpers.mjs`) live alongside.
Keep test data inline when practical; see the Fixture policy section in PYTEST_STYLE.md.

Pytest only collects `test_*.py` files and actively excludes `tests/playwright/`
via `collect_ignore = ["e2e", "playwright"]` in `tests/conftest.py`, so the extension
and subfolder together ensure Playwright scripts stay outside the fast pytest lane.

## Optional: full-path Playwright walkthroughs

Some repos group complete Playwright walkthroughs (multi-step user journeys, recovery scenarios, full protocol runs) in `tests/playwright/e2e/`. This is an **optional sub-grouping**: use it only when you have multiple full-path walkthroughs worth grouping together. If you have just one or two, keep them flat in `tests/playwright/`. The same E2E exclusion applies: both `tests/playwright/` and its children are excluded from pytest collection.

## Packages

| Package | Purpose |
| --- | --- |
| `playwright` | Library/API for browser automation (what we use) |
| `@playwright/test` | Test runner with fixtures, assertions, reporters |
| `playwright-core` | Low-level core without bundled browsers (rarely needed) |

Playwright's "fixtures" are a framework feature of `@playwright/test` (test-runner setup and
teardown helpers); for repo test data design, follow the Fixture policy section in
PYTEST_STYLE.md (inline setup first).

For "open a local HTML file, click things, take screenshots", use `playwright`.

## Script template

```javascript
import { chromium } from 'playwright';
import path from 'path';

const gamePath = path.resolve('cell_culture_game.html');
const url = `file://${gamePath}`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
await page.goto(url);
await page.waitForTimeout(500);

// Interact with the page
await page.click('#welcome-start-btn');
await page.waitForTimeout(300);

// Screenshot
await page.screenshot({ path: 'test-results/screenshot.png' });

// Measure element positions
const box = await page.locator('#my-element').boundingBox();
console.log('Position:', box);

await browser.close();
```

Run with:

```bash
node tests/playwright/my_test.mjs
```

## Headless by default

The canonical pattern above uses `chromium.launch()` with no arguments, which
defaults to `headless: true`. Existing scripts already run headless; do not
"fix" them.

Rule for agents:

- Do not pass `headless: false` to `chromium.launch()`.
- Do not add `--headed` to invocations.
- The default is correct.

If a human is debugging locally and explicitly wants to watch the browser,
they can pass `headless: false` themselves. Agents should not do this on
their behalf.

## Common patterns

### Click a hood item

Hood items use `data-item-id`:

```javascript
await page.click('[data-item-id="ethanol_bottle"]');
```

### Wait for animations

Use `waitForTimeout` after actions that trigger animations:

```javascript
await page.click('[data-item-id="flask"]');
await page.waitForTimeout(2500);  // aspiration takes ~2s
```

### Check element alignment

Use `boundingBox()` to compare positions of overlapping elements:

```javascript
const svgRect = await page.locator('#microscope-svg rect[fill="#e8f5e9"]').first().boundingBox();
const button = await page.locator('.quadrant-btn').first().boundingBox();
const dx = Math.abs(svgRect.x - button.x);
const dy = Math.abs(svgRect.y - button.y);
console.log(`Offset: dx=${dx.toFixed(1)} dy=${dy.toFixed(1)}`);
```

### Evaluate JavaScript in the page

```javascript
const result = await page.evaluate(() => {
    return document.querySelectorAll('.quadrant-btn').length;
});
console.log('Button count:', result);
```

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `Cannot find module 'playwright'` | Run the script from the project root, not `/tmp/` |
| `browserType.launch: Executable doesn't exist` | Run `npx playwright install` |
| `npx playwright` works but `node script.mjs` fails | Different issue: npx resolves packages differently than Node require |
| Timeout clicking an element | Check the selector; use `data-item-id` not `data-item` for hood items |
| Browser windows pop up during test runs | An agent added `headless: false` or `--headed`; remove it. Default is headless. |

## Verify install

```bash
npm ls playwright
```

Should show `playwright@x.x.x` under the project.

## File conventions

- Put Playwright scripts in `tests/playwright/` at the repo root.
- `tests/playwright/` is tool-named: it groups all browser-driven tests regardless of scope (smoke, layout, regression, walkthroughs). Future browser tools (Cypress, Puppeteer) would each get their own tool-named folder; do NOT lump them under `tests/playwright/`.
- Filenames inside `tests/playwright/` are unconstrained: `test_*.mjs` for tests, `helpers.mjs` for shared utilities, `build_*.mjs` for bootstrap scripts, `*_walkthrough.mjs` for walkthroughs all coexist legitimately. The only restriction enforced by `tests/test_test_naming_conventions.py` is that any file with a Playwright import must live under `tests/playwright/`.
- Use `.mjs` extension for ES module scripts (e.g., `tests/playwright/test_game_ui.mjs`).
- Put screenshots in `test-results/` (gitignored).
- Note: `tests/conftest.py` declares `collect_ignore = ["e2e", "playwright"]` so pytest never collects anything in this tree, regardless of name.

## PDF generation

Render HTML to PDF using `tools/html_to_pdf.mjs`. Run it directly with node:

```bash
node tools/html_to_pdf.mjs --input report.html --output test-results/report.pdf
```

The `--output` flag is optional. If not provided, the CLI derives the output filename by replacing the input's extension with `.pdf` in the same directory:

```bash
node tools/html_to_pdf.mjs --input report.html
# writes report.pdf alongside report.html
```

When `--input` is an `http://`, `https://`, or `file://` URL, `--output` is required - the filename cannot be derived from a URL.

Generate landscape orientation by adding the `--landscape` flag:

```bash
node tools/html_to_pdf.mjs --input wide.html --output /tmp/wide.pdf --landscape
```

Hardcoded defaults: Letter page size, 0.6 inch margins, screen media, 1440 x 1200 pixel viewport, `networkidle` wait, and backgrounds enabled.

Write PDFs to `/tmp/` or `test-results/` - both are gitignored.

Chromium only. Firefox and WebKit do not implement `page.pdf()`.

The tool needs the `playwright` dev dependency. If it is not installed yet:

```bash
npm install --save-dev playwright
```
