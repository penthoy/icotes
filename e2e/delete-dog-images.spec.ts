import { test, expect, Page, Locator } from '@playwright/test';

const APP_URL = 'http://192.168.2.203:8000/';

// Visible filenames we saw in your workspace. We will try these first and also fall back to regex discovery.
const DOG_FILES = [
  'dog_green_bg.png',
  'dog_photo_2d.png',
  'dog_photo_nobg.png',
  'dog_photo.png',
  'dog_transparent.png',
  'dog_with_green_hat.png',
  'dog_with_hat.png',
  'dog_with_red_hat.png',
];

async function clickFirstAvailable(page: Page, getLocator: () => Locator[], timeout = 4000) {
  const deadline = Date.now() + timeout;
  // Try all provided locators in sequence; click the first that exists.
  while (Date.now() < deadline) {
    for (const loc of getLocator()) {
      const count = await loc.count();
      if (count > 0) {
        await loc.first().click();
        return true;
      }
    }
    await page.waitForTimeout(150);
  }
  return false;
}

async function openContextMenuOnFile(page: Page, filename: string) {
  const explorerRoot = page.locator('[data-explorer-root]');
  // Try multiple ways to locate a file row by visible text
  const candidates: Locator[] = [
    explorerRoot.getByText(filename, { exact: true }),
    explorerRoot.locator(`text=${filename}`),
    explorerRoot.locator(`[title="${filename}"]`),
    explorerRoot.locator(`[data-filename="${filename}"]`),
  ];

  // Ensure at least one candidate is visible
  let found = false;
  for (const c of candidates) {
    if (await c.first().isVisible().catch(() => false)) { found = true; break; }
  }
  if (!found) {
    // Last resort: search using regex across any text nodes in explorer area
    const regexLoc = page.locator('text=/^' + filename.replace(/[.*+?^${}()|[\]\\]/g, r => `\\${r}`) + '$/');
    if (await regexLoc.count() > 0) candidates.unshift(regexLoc);
  }

  // Right-click the first visible match
  for (const c of candidates) {
    if (await c.first().isVisible().catch(() => false)) {
      await c.first().click({ button: 'right' });
      return true;
    }
  }
  return false;
}

async function clickDeleteInContextMenu(page: Page) {
  // Wait for a menu to appear and try common labels
  const menu = page.locator('.icui-context-menu');
  await menu.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {});
  const options = [
    menu.getByRole('menuitem', { name: /^Delete$/i }),
    menu.getByRole('menuitem', { name: /delete/i }),
    menu.getByRole('menuitem', { name: /remove/i }),
    menu.getByText(/^Delete$/i),
    menu.getByText(/delete/i),
    menu.getByText(/remove/i),
  ];
  for (const opt of options) {
    if (await opt.count() > 0) {
      await opt.first().click();
      return true;
    }
  }
  return false;
}

async function confirmDeletionIfPrompted(page: Page) {
  // Some UIs open a confirmation dialog
  const dialog = page.getByRole('dialog');
  if (await dialog.count()) {
    const confirmButtons = [
      dialog.getByRole('button', { name: /delete/i }),
      dialog.getByRole('button', { name: /remove/i }),
      dialog.getByRole('button', { name: /confirm/i }),
      dialog.getByRole('button', { name: /yes/i }),
      page.getByRole('button', { name: /delete/i }),
      page.getByRole('button', { name: /remove/i }),
    ];
    for (const btn of confirmButtons) {
      if (await btn.count()) {
        await btn.first().click();
        return;
      }
    }
  }
}

// Utility to discover any dog_* files by scanning visible text in the Explorer list.
async function discoverDogFiles(page: Page) {
  const matches: string[] = [];
  const candidate = page.locator('[data-explorer-root] >> text=/^dog_.*\.(png|jpe?g|webp)$/i');
  const n = await candidate.count();
  for (let i = 0; i < n; i++) {
    const t = (await candidate.nth(i).innerText().catch(() => ''))?.trim();
    if (t && /^dog_.*\.(png|jpe?g|webp)$/i.test(t)) matches.push(t);
  }
  return Array.from(new Set(matches));
}

// Main test
// It attempts dynamic discovery first; if none found, falls back to known filenames from the screenshot.

test('delete all dog_* images from Explorer via context menu', async ({ page }) => {
  test.setTimeout(120000);

  await page.goto(APP_URL, { waitUntil: 'domcontentloaded' });

  // Wait for the Explorer to render (look for any known file as a heuristic)
  const explorerRoot = page.locator('[data-explorer-root]');
  await expect(explorerRoot).toBeVisible({ timeout: 15000 });
  await expect(explorerRoot.getByText('README.md')).toBeVisible({ timeout: 15000 }).catch(() => {});

  const discovered = await discoverDogFiles(page);
  const targets = discovered.length ? discovered : DOG_FILES;

  for (const filename of targets) {
    // If item not visible, skip quietly
    const row = explorerRoot.getByText(filename, { exact: true });
    const visible = await row.first().isVisible().catch(() => false);
    if (!visible) continue;

    // Open context menu on the row
    const opened = await openContextMenuOnFile(page, filename);
    if (!opened) continue;

    // Choose Delete/Remove
    await clickDeleteInContextMenu(page);

    // Confirm if a dialog appears
    await confirmDeletionIfPrompted(page);

    // Wait for the item to disappear from the Explorer (scope to explorer to avoid dialog/toast text)
    await expect(explorerRoot.getByText(filename, { exact: true })).toHaveCount(0, { timeout: 15000 });
  }
});
