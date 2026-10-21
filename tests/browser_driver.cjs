/* CI adapter for real Playwright: only bounded waits, no event/HTTP mocks. */
'use strict';
const real = process.env.PLAYWRIGHT_PACKAGE;
if (!real) throw new Error('PLAYWRIGHT_PACKAGE must name the pinned Playwright package');
const playwright = require(real);
const launch = playwright.chromium.launch.bind(playwright.chromium);
playwright.chromium.launch = async options => {
  const browser = await launch(options), configured = new WeakSet();
  const setup = page => {
    if (configured.has(page)) return page;
    configured.add(page);
    page.setDefaultTimeout(8000);
    page.setDefaultNavigationTimeout(15000);
    return page;
  };
  const newPage = browser.newPage.bind(browser);
  browser.newPage = async options => setup(await newPage(options));
  const newContext = browser.newContext.bind(browser);
  browser.newContext = async options => {
    const context = await newContext(options), newContextPage = context.newPage.bind(context);
    context.newPage = async () => setup(await newContextPage());
    return context;
  };
  return browser;
};
module.exports = playwright;
