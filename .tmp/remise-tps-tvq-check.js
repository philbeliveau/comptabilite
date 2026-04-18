const { chromium } = require('/opt/homebrew/lib/node_modules/playwright');

const BASE = 'http://127.0.0.1:5001/compteqc-corporation-consultation-it-quebec';

async function textOf(page, selector) {
  const el = await page.locator(selector).first();
  return (await el.textContent()) || '';
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });

  const receiptUrl = `${BASE}/extension/RecusExtension/`;
  await page.goto(receiptUrl, { waitUntil: 'networkidle' });
  await page.waitForSelector('h2');

  const receiptHeader = await textOf(page, 'h2');
  const receiptHasTypeSelect = await page.locator('#document-kind-select').count();
  await page.selectOption('#document-kind-select', 'revenue');
  const pricingVisible = await page.locator('#pricing-mode-wrap').evaluate(
    (el) => getComputedStyle(el).display !== 'none'
  );
  const reviewSection = await page.locator('text=Documents revenus à revoir').count();
  await page.screenshot({ path: '.tmp/receipt-revenue-flow.png', fullPage: true });

  const arUrl = `${BASE}/extension/ComptesFournisseursExtension/?prefill=1&tab=ar&nom_client=PROCOM%20SERVICES&date=2026-03-11&description=Services%20consultation&montant=1000.00&tps_applicable=1&tvq_applicable=1&notes=Document%20revenu`;
  await page.goto(arUrl, { waitUntil: 'networkidle' });
  await page.waitForSelector('#ar-form');
  const clientValue = await page.locator('[name="nom_client"]').inputValue();
  const amountValue = await page.locator('[name="prix_unitaire_0"]').inputValue();
  const tpsChecked = await page.locator('[name="tps_0"]').isChecked();
  const tvqChecked = await page.locator('[name="tvq_0"]').isChecked();
  await page.screenshot({ path: '.tmp/ar-prefill-flow.png', fullPage: true });

  const taxesUrl = `${BASE}/extension/TaxesQCExtension/?periode=2026-Q1`;
  await page.goto(taxesUrl, { waitUntil: 'networkidle' });
  await page.waitForSelector('h2');
  const taxesHeader = await textOf(page, 'h2');
  const reviewTextCount = await page.locator('text=Revue revenus/taxes').count();
  const warningTextCount = await page.locator('text=Revenus sans split fiscal explicite').count();
  await page.screenshot({ path: '.tmp/remise-revenue-audit.png', fullPage: true });

  await browser.close();

  console.log(JSON.stringify({
    receiptHeader,
    receiptHasTypeSelect,
    pricingVisible,
    reviewSection,
    clientValue,
    amountValue,
    tpsChecked,
    tvqChecked,
    taxesHeader,
    reviewTextCount,
    warningTextCount,
  }, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
