import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('C:/Users/localhost/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.js');
const [htmlPath, outDir] = process.argv.slice(2);
if (!htmlPath || !outDir) throw new Error('usage: node _v13_visual_check.mjs <html> <outdir>');
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
});
const required = ['today','market','themes','portfolio','opportunities','events','goals','learning','lookup','sources'];

async function inspect(name, viewport) {
  const page = await browser.newPage({ viewport });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto(pathToFileURL(path.resolve(htmlPath)).href, { waitUntil: 'load' });

  const initial = await page.evaluate(requiredIds => {
    const nav = [...document.querySelectorAll('nav a[href^="#"]')];
    const details = [...document.querySelectorAll('details')];
    const tables = [...document.querySelectorAll('table')];
    return {
      title: document.title,
      sectionCount: requiredIds.filter(id => document.getElementById(id)).length,
      navCount: nav.length,
      missingNavAnchors: nav.filter(link => !document.querySelector(link.getAttribute('href'))).length,
      holdings: document.querySelectorAll('[data-holding="1"]').length,
      opportunities: document.querySelectorAll('[data-opportunity="1"]').length,
      assets: document.querySelectorAll('[data-asset="1"]').length,
      themes: document.querySelectorAll('[data-theme="1"]').length,
      details: details.length,
      initiallyClosed: details.every(item => !item.open),
      tables: tables.length,
      unwrappedWideTables: tables.filter(table => !table.closest('.table-wrap') && table.scrollWidth > table.clientWidth + 1).length,
      blankSections: requiredIds.filter(id => !document.getElementById(id)?.innerText.trim()).length,
      bodyTextLength: document.body.innerText.length,
    };
  }, required);

  const interaction = await page.evaluate(() => {
    const details = [...document.querySelectorAll('details')];
    details.forEach(item => item.open = true);
    const allOpen = details.every(item => item.open);
    details.forEach(item => item.open = false);
    return { allOpen, allClosed: details.every(item => !item.open) };
  });

  const navChecks = [];
  for (const id of ['today','portfolio','goals','sources']) {
    await page.locator(`nav a[href="#${id}"]`).click();
    await page.waitForTimeout(80);
    navChecks.push(await page.evaluate(sectionId => {
      const element = document.getElementById(sectionId);
      return { id: sectionId, found: Boolean(element), top: element ? Math.round(element.getBoundingClientRect().top) : null };
    }, id));
  }

  const layout = await page.evaluate(() => ({
    documentOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    wideElements: [...document.querySelectorAll('body *')]
      .filter(item => {
        const rect = item.getBoundingClientRect();
        return rect.right > window.innerWidth + 2 || rect.left < -2;
      })
      .slice(0, 20)
      .map(item => ({ tag: item.tagName, cls: item.className, text: (item.textContent || '').trim().slice(0, 80), left: Math.round(item.getBoundingClientRect().left), right: Math.round(item.getBoundingClientRect().right), scrollWidth: item.scrollWidth, clientWidth: item.clientWidth })),
    clippedTextBlocks: [...document.querySelectorAll('h1,h2,h3,p,span,small,td,th')].filter(
      item => item.scrollWidth > item.clientWidth + 2 && !item.closest('.table-wrap') && getComputedStyle(item).whiteSpace !== 'nowrap'
    ).length,
    zeroHeightSections: [...document.querySelectorAll('main>section')].filter(item => item.getBoundingClientRect().height < 40).length,
  }));

  for (const id of ['today','portfolio','goals','sources']) {
    await page.locator(`#${id}`).scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(outDir, `${name}_${id}.png`), fullPage: false });
  }

  const status = initial.sectionCount === 10
    && initial.navCount === 10
    && initial.missingNavAnchors === 0
    && initial.holdings === 24
    && initial.opportunities === 18
    && initial.assets === 42
    && initial.themes === 4
    && initial.details >= 1
    && initial.initiallyClosed
    && initial.unwrappedWideTables === 0
    && initial.blankSections === 0
    && initial.bodyTextLength > 30000
    && interaction.allOpen
    && interaction.allClosed
    && navChecks.every(item => item.found)
    && !layout.documentOverflow
    && layout.clippedTextBlocks === 0
    && layout.zeroHeightSections === 0
    && errors.length === 0 ? 'PASS' : 'FAIL';

  await page.close();
  return { viewport, initial, interaction, navChecks, layout, errors, status };
}

const result = {
  actualBrowser: 'Microsoft Edge via Playwright',
  desktop: await inspect('desktop', { width: 1410, height: 900 }),
  mobile390: await inspect('mobile390', { width: 390, height: 844 }),
};
result.status = result.desktop.status === 'PASS' && result.mobile390.status === 'PASS' ? 'PASS' : 'FAIL';
fs.writeFileSync(path.join(outDir, 'V13导航与浏览器测试.json'), JSON.stringify(result, null, 2), 'utf8');
console.log(JSON.stringify(result, null, 2));
await browser.close();
