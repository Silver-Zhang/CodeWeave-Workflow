/* Real Playwright adapter for CI: bound waits instead of hanging until the
 * outer process timeout. No page, HTTP response, event or assertion is mocked.
 * Individual suites may choose a stricter timeout after page creation.
 */
'use strict';
const real = process.env.PLAYWRIGHT_PACKAGE;
if (!real) throw new Error('PLAYWRIGHT_PACKAGE must name the actual pinned Playwright package');
const playwright = require(real);
const launch = playwright.chromium.launch.bind(playwright.chromium);
playwright.chromium.launch = async options => {
  const browser = await launch(options);
  const setup = page => {
    page.setDefaultTimeout(8000);
    page.setDefaultNavigationTimeout(15000);
    return page;
  };
  const newPage = browser.newPage.bind(browser);
  browser.newPage = async options => setup(await newPage(options));
  const newContext = browser.newContext.bind(browser);
  browser.newContext = async options => {
    const context = await newContext(options);
    const page = context.newPage.bind(context);
    context.newPage = async () => setup(await page());
    return context;
  };
  return browser;
};
module.exports = playwright;
