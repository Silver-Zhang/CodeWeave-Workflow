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
    // Progress diagnostics remain synthetic-test metadata, never application data.
    const locator = page.locator.bind(page);
    page.locator = (...args) => {
      const value = locator(...args), drag = value.dragTo.bind(value);
      value.dragTo = async (target, options) => {
        console.log('BROWSER dragTo begin ' + args[0]);
        await page.screenshot({path:require('path').join(process.argv[2],'before-native-drag.png')});
        try { return await drag(target, {...options, timeout:8000}); }
        finally { console.log('BROWSER dragTo settled ' + args[0]); }
      };
      return value;
    };
    const wait = page.waitForFunction.bind(page);
    page.waitForFunction = (fn, arg, options) => wait(fn, arg, {timeout:8000, ...options});
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
