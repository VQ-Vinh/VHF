// Run against locally rendered responsive_fixtures.py output, never production.
// PLAYWRIGHT_MODULE may point to an existing Playwright installation.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.BROWSER_EXECUTABLE ? { executablePath: process.env.BROWSER_EXECUTABLE } : {}) });
  const page = await browser.newPage({ reducedMotion: 'reduce' });
  const failures = [];
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => {
    const request = route.request();
    if (!request.url().startsWith('http://127.0.0.1:8875/') || request.method() !== 'GET') return route.abort();
    return route.continue();
  });
  const output = 'build/buildapp/responsive-web';
  let cases = 0;
  async function check(label) {
    const overflow = await page.evaluate(() => {
      const width = document.documentElement.clientWidth;
      return [...document.querySelectorAll('body *')].filter(element => {
        const style = getComputedStyle(element);
        if (style.visibility === 'hidden' || style.display === 'none') return false;
        if (element.closest('thead') && getComputedStyle(element.closest('thead')).position === 'absolute') return false;
        const box = element.getBoundingClientRect();
        return box.width > 0 && (box.right > width + 1 || box.left < -1);
      }).map(element => `${element.tagName}.${element.className}`).slice(0, 12);
    });
    if (overflow.length) failures.push({ label, overflow });
    cases++;
  }
  for (const locale of ['vi', 'en']) {
    for (const name of ['dashboard', 'users', 'user_detail', 'stations', 'station_detail', 'plans', 'audit', 'error']) {
      await page.goto(`http://127.0.0.1:8875/${locale}-${name}.html`);
      await page.evaluate(() => {
        window.fontSizes = [...document.querySelectorAll('body *')].map(element => [element, parseFloat(getComputedStyle(element).fontSize), getComputedStyle(element).lineHeight]);
      });
      for (const width of [320, 375, 390, 400, 430, 768, 1024, 1440, 1920]) {
        await page.setViewportSize({ width, height: 800 });
        for (const scale of [1, 1.5, 2]) {
          await page.evaluate(scale => {
            for (const [element, font, line] of window.fontSizes) {
              element.style.fontSize = `${font * scale}px`;
              if (line !== 'normal') element.style.lineHeight = `${parseFloat(line) * scale}px`;
            }
          }, scale);
          await check(`${locale}/${name}/${width}/text-${scale}`);
        }
        await page.evaluate(() => { for (const [element] of window.fontSizes) { element.style.removeProperty('font-size'); element.style.removeProperty('line-height'); } });
        if (locale === 'vi' && [320, 768, 1440].includes(width)) {
          await page.screenshot({ path: path.join(output, `${name}-${width}.png`), fullPage: true });
        }
      }
      await page.setViewportSize({ width: 800, height: 320 });
      await check(`${locale}/${name}/landscape`);
    }
  }
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('http://127.0.0.1:8875/vi-plans.html');
  await page.locator('[data-menu-button]').click();
  await page.locator('.sidebar').evaluate(element => Promise.all(element.getAnimations().map(animation => animation.finished)));
  await check('menu open');
  await page.keyboard.press('Escape');
  if (await page.locator('[data-menu-button]').getAttribute('aria-expanded') !== 'false') failures.push('Menu Escape');
  await page.locator('[data-plan-edit]').first().click();
  await page.locator('input[name="name"]').first().fill('Synthetic edited plan');
  await page.locator('[data-plan-preview]').first().click();
  await check('confirmation dialog');
  if (!await page.locator('[data-confirm-dialog]').isVisible()) failures.push('Missing confirmation');
  await page.keyboard.press('Escape');
  if (await page.locator('input[name="name"]').first().inputValue() !== 'Synthetic edited plan') failures.push('Draft lost');
  fs.writeFileSync(path.join(output, 'measurements.json'), JSON.stringify({ cases, errors, failures }, null, 2));
  console.log(JSON.stringify({ cases, errors, failures }, null, 2));
  await browser.close();
  if (failures.length || errors.length) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
