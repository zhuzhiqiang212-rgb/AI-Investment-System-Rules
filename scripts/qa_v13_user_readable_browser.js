const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

const [htmlPath, reportPath, outDir] = process.argv.slice(2);
if (!htmlPath || !reportPath || !outDir) process.exit(2);

(async () => {
  let browser;
  const views = [];
  try {
    fs.mkdirSync(outDir, { recursive: true });
    browser = await chromium.launch({ channel: 'msedge', headless: true });
    for (const viewport of [
      { name: 'desktop', width: 1410, height: 900 },
      { name: 'mobile390', width: 390, height: 844 },
    ]) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
      page.on('pageerror', error => errors.push(String(error)));
      await page.goto(pathToFileURL(path.resolve(htmlPath)).href, { waitUntil: 'load', timeout: 60000 });
      const initial = await page.evaluate(() => ({
        title: document.title,
        sections: document.querySelectorAll('main > section').length,
        navLinks: document.querySelectorAll('.nav a[href^="#"]').length,
        missingNavAnchors: [...document.querySelectorAll('.nav a[href^="#"]')].filter(a => !document.querySelector(a.getAttribute('href'))).length,
        holdings: document.querySelectorAll('[data-holding="1"]').length,
        opportunities: document.querySelectorAll('[data-opportunity="1"]').length,
        assets: document.querySelectorAll('[data-asset="1"]').length,
        themes: document.querySelectorAll('[data-theme="1"]').length,
        waveA: document.querySelectorAll('[data-wave-grade="A"]').length,
        waveB: document.querySelectorAll('[data-wave-grade="B"]').length,
        waveC: document.querySelectorAll('[data-wave-grade="C"]').length,
        eventCalendar: document.querySelectorAll('[data-event-calendar="1"]').length,
        oldARegrades: document.querySelectorAll('[data-old-a-regrade="1"]').length,
        details: document.querySelectorAll('details').length,
        initiallyClosed: document.querySelectorAll('details[open]').length === 0,
      }));
      await page.evaluate(() => document.querySelectorAll('details').forEach(item => { item.open = true; }));
      const expanded = await page.evaluate(() => document.querySelectorAll('details[open]').length);
      const layout = await page.evaluate(() => {
        const tableMismatches = [];
        [...document.querySelectorAll('table')].forEach((table, tableIndex) => {
          const columns = table.querySelectorAll(':scope > thead > tr:last-child > th').length;
          [...table.querySelectorAll(':scope > tbody > tr')].forEach((row, rowIndex) => {
            const cells = row.querySelectorAll(':scope > td, :scope > th').length;
            if (columns && columns !== cells) tableMismatches.push({ tableIndex, rowIndex, columns, cells });
          });
        });
        const unwrappedWide = [...document.querySelectorAll('body *')].filter(element => {
          if (element.closest('.table-wrap') || element.closest('.nav')) return false;
          const box = element.getBoundingClientRect();
          return box.width > 0 && (box.right > document.documentElement.clientWidth + 3 || box.left < -3);
        }).slice(0, 20).map(element => ({ tag: element.tagName, className: element.className, text: (element.textContent || '').trim().slice(0, 80) }));
        const visibleText = document.body.innerText;
        return {
          documentOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 3,
          unwrappedWide,
          tableMismatches,
          replacementCharacters: (visibleText.match(/\uFFFD/g) || []).length,
          obsoleteA21Meaning: visibleText.includes('21项A级投资机会'),
          plus100MethodConclusion: visibleText.includes('目前不能计算+100%') || visibleText.includes('现在仍不能计算+100%'),
          bodyTextLength: visibleText.length,
        };
      });
      await page.evaluate(() => document.querySelectorAll('details').forEach(item => { item.open = false; }));
      const collapsed = await page.evaluate(() => document.querySelectorAll('details[open]').length);
      const screenshot = path.join(outDir, `V13_${viewport.name}_plus100_v2.png`);
      await page.screenshot({ path: screenshot, fullPage: true });
      const goalsScreenshot = path.join(outDir, `V13_${viewport.name}_goals_v2.png`);
      await page.locator('#goals').screenshot({ path: goalsScreenshot });
      const pass = initial.sections === 10 && initial.navLinks === 10 && initial.missingNavAnchors === 0
        && initial.holdings === 24 && initial.opportunities === 18 && initial.assets === 42 && initial.themes === 4
        && initial.waveA === 3 && initial.waveB === 39 && initial.waveC === 0
        && initial.eventCalendar === 42 && initial.oldARegrades === 21
        && initial.initiallyClosed && expanded === initial.details && collapsed === 0
        && !layout.documentOverflow && layout.unwrappedWide.length === 0 && layout.tableMismatches.length === 0
        && layout.replacementCharacters === 0 && !layout.obsoleteA21Meaning && layout.plus100MethodConclusion
        && errors.length === 0;
      views.push({ viewport, initial, expanded, collapsed, layout, errors, screenshot, goalsScreenshot, pass });
      await page.close();
    }
    const result = {
      actualBrowser: 'Microsoft Edge via Playwright',
      checkedAt: new Date().toISOString(),
      status: views.every(view => view.pass) ? 'PASS' : 'FAIL',
      views,
    };
    fs.writeFileSync(reportPath, JSON.stringify(result, null, 2), 'utf8');
    process.exitCode = result.status === 'PASS' ? 0 : 1;
  } catch (error) {
    fs.writeFileSync(reportPath, JSON.stringify({ status: 'BLOCKED', error: String(error) }, null, 2), 'utf8');
    process.exitCode = 2;
  } finally {
    if (browser) await browser.close();
  }
})();
