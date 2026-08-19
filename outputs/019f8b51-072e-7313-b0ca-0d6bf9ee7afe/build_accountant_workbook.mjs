import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = "/Users/philippebeliveau/Downloads/Template- QC and ON business income-Sales and Exp invoices.xlsx";
const outputDir = "/Users/philippebeliveau/Desktop/Notebook/comptabilite/outputs/019f8b51-072e-7313-b0ca-0d6bf9ee7afe";
const outputPath = `${outputDir}/Accountant-business-income-sales-expenses-2025-11-to-2026-07.xlsx`;

const rows = [
  ["Colleen Marie Yfggzs", new Date("2026-03-02T12:00:00"), 355.00, 0, 0, 355.00, "NO Tax", "5.8-Rent"],
  ["Fizz", new Date("2026-03-04T12:00:00"), 21.50, 1.08, 2.14, 24.72, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Boi Lab 003 Inc.", new Date("2026-03-10T12:00:00"), 210.11, 10.51, 20.96, 241.58, "Quebec (GST/QST)", "4.1- Sales Revenue(contact)"],
  ["CRL", new Date("2026-03-11T12:00:00"), 2000.00, 100.00, 199.50, 2299.50, "Quebec (GST/QST)", "4.1- Sales Revenue(contact)"],
  ["Eric Vuong", new Date("2026-03-14T12:00:00"), 2750.00, 0, 0, 2750.00, "NO Tax", "1.4-Assets-Computer"],
  ["Microsoft", new Date("2026-03-19T12:00:00"), 2.30, 0, 0, 2.30, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Fizz", new Date("2026-03-29T12:00:00"), 11.28, 0.56, 1.13, 12.97, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Google One", new Date("2026-03-30T12:00:00"), 15.51, 0, 0, 15.51, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Frais Annuels RBC", new Date("2026-04-01T12:00:00"), 175.00, 0, 0, 175.00, "NO Tax", "5.2-Bank Charges and Interest"],
  ["Frais Mensuels RBC", new Date("2026-04-01T12:00:00"), 6.00, 0, 0, 6.00, "NO Tax", "5.2-Bank Charges and Interest"],
  ["Google Cloud", new Date("2026-04-01T12:00:00"), 42.75, 0, 0, 42.75, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Fizz", new Date("2026-04-04T12:00:00"), 21.50, 1.08, 2.14, 24.72, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Colleen Marie Gru69U", new Date("2026-04-06T12:00:00"), 355.00, 0, 0, 355.00, "NO Tax", "5.8-Rent"],
  ["Procom", new Date("2026-04-10T12:00:00"), 9680.00, 484.00, 965.58, 11129.58, "Quebec (GST/QST)", "4.1- Sales Revenue(contact)"],
  ["Microsoft", new Date("2026-04-19T12:00:00"), 2.30, 0, 0, 2.30, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Fizz", new Date("2026-04-28T12:00:00"), 11.28, 0.56, 1.13, 12.97, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Frais Mensuels RBC", new Date("2026-05-01T12:00:00"), 6.00, 0, 0, 6.00, "NO Tax", "5.2-Bank Charges and Interest"],
  ["Google Cloud", new Date("2026-05-01T12:00:00"), 0.03, 0, 0, 0.03, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Colleen Marie 4Qc43D", new Date("2026-05-04T12:00:00"), 355.00, 0, 0, 355.00, "NO Tax", "5.8-Rent"],
  ["Fizz", new Date("2026-05-04T12:00:00"), 21.50, 1.08, 2.14, 24.72, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Anthropic", new Date("2026-05-04T12:00:00"), 9.61, 0, 0, 9.61, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Procom", new Date("2026-05-08T12:00:00"), 18150.00, 907.50, 1810.46, 20867.96, "Quebec (GST/QST)", "4.1- Sales Revenue(contact)"],
  ["Microsoft", new Date("2026-05-19T12:00:00"), 2.30, 0, 0, 2.30, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Fizz", new Date("2026-05-22T12:00:00"), 0.50, 0.03, 0.05, 0.58, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Fizz", new Date("2026-05-29T12:00:00"), 11.28, 0.56, 1.13, 12.97, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Frais Mensuels RBC", new Date("2026-06-01T12:00:00"), 6.00, 0, 0, 6.00, "NO Tax", "5.2-Bank Charges and Interest"],
  ["Colleen Marie Fedwe8", new Date("2026-06-01T12:00:00"), 355.00, 0, 0, 355.00, "NO Tax", "5.8-Rent"],
  ["Google Cloud", new Date("2026-06-01T12:00:00"), 0.65, 0, 0, 0.65, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Fizz", new Date("2026-06-04T12:00:00"), 21.50, 1.08, 2.14, 24.72, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Procom", new Date("2026-06-05T12:00:00"), 11165.00, 558.25, 1113.71, 12836.96, "Quebec (GST/QST)", "4.1- Sales Revenue(contact)"],
  ["Microsoft", new Date("2026-06-19T12:00:00"), 2.30, 0, 0, 2.30, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Google Cloud", new Date("2026-07-01T12:00:00"), 1.01, 0, 0, 1.01, "NO Tax", "5.9-Memebership and Subscriptions"],
  ["Frais Mensuels RBC", new Date("2026-07-02T12:00:00"), 6.00, 0, 0, 6.00, "NO Tax", "5.2-Bank Charges and Interest"],
  ["Fizz", new Date("2026-07-04T12:00:00"), 21.50, 1.08, 2.14, 24.72, "Quebec (GST/QST)", "5.10-Telephone and Internet"],
  ["Restaurant Novello", new Date("2026-07-10T12:00:00"), 243.05, 0, 0, 243.05, "NO Tax", "5.16-Meals and Entertainment"],
  ["Procom", new Date("2026-07-10T12:00:00"), 16830.00, 841.50, 1678.79, 19350.29, "Quebec (GST/QST)", "4.1- Sales Revenue(contact)"],
];

await fs.mkdir(outputDir, { recursive: true });
const input = await FileBlob.load(sourcePath);
const workbook = await SpreadsheetFile.importXlsx(input);
const transactions = workbook.worksheets.getItem("Transactions");

transactions.getRange("A2:H1000").clear({ applyTo: "contents" });
transactions.getRange("C2:E1000").clear({ applyTo: "contents" });
transactions.getRange(`C2:E${rows.length + 1}`).formulas = rows.map(() => ["", "", ""]);
transactions.getRange(`A2:H${rows.length + 1}`).writeValues(rows);
transactions.getRange("C5").formulas = [["=IF(OR(F5=\"\",G5=\"\"),\"\",IF(G5=\"NO Tax\",F5,IF(G5=\"Quebec (GST/QST)\",ROUND(F5/1.14975,2),IF(G5=\"Ontario(GST/HST)\",ROUND(F5/1.13,2),\"N/A\"))))"]];
transactions.getRange("D5").formulas = [["=IF(OR(F5=\"\",G5=\"\"),\"\",IF(G5=\"NO Tax\",0,IF(G5=\"Quebec (GST/QST)\",ROUND(C5*5%,2),IF(G5=\"Ontario(GST/HST)\",ROUND(C5*13%,2),\"N/A\"))))"]];
transactions.getRange("E5").formulas = [["=IF(OR(F5=\"\",G5=\"\"),\"\",IF(G5=\"NO Tax\",0,IF(G5=\"Quebec (GST/QST)\",ROUND(F5-C5-D5,2),IF(G5=\"Ontario(GST/HST)\",0,\"N/A\"))))"]];
transactions.getRange(`B2:B${rows.length + 1}`).format.numberFormat = "yyyy-mm-dd";
transactions.getRange(`C2:F${rows.length + 1}`).format.numberFormat = "$#,##0.00";
transactions.getRange("B1:B1000").format.columnWidth = 14;
transactions.getRange("G2:G1000").dataValidation = {
  rule: { type: "list", formula1: "'Validation List'!$C$1:$C$3" },
};
transactions.getRange("H2:H1000").dataValidation = {
  rule: { type: "list", formula1: "'Validation List'!$A$1:$A$28" },
};

const firstFutureRow = rows.length + 2;
transactions.getRange(`C${firstFutureRow}`).formulas = [[`=IF(OR(F${firstFutureRow}="",G${firstFutureRow}=""),"",IF(G${firstFutureRow}="NO Tax",F${firstFutureRow},IF(G${firstFutureRow}="Quebec (GST/QST)",ROUND(F${firstFutureRow}/1.14975,2),IF(G${firstFutureRow}="Ontario(GST/HST)",ROUND(F${firstFutureRow}/1.13,2),"N/A"))))`]];
transactions.getRange(`D${firstFutureRow}`).formulas = [[`=IF(OR(F${firstFutureRow}="",G${firstFutureRow}=""),"",IF(G${firstFutureRow}="NO Tax",0,IF(G${firstFutureRow}="Quebec (GST/QST)",ROUND(C${firstFutureRow}*5%,2),IF(G${firstFutureRow}="Ontario(GST/HST)",ROUND(C${firstFutureRow}*13%,2),"N/A"))))`]];
transactions.getRange(`E${firstFutureRow}`).formulas = [[`=IF(OR(F${firstFutureRow}="",G${firstFutureRow}=""),"",IF(G${firstFutureRow}="NO Tax",0,IF(G${firstFutureRow}="Quebec (GST/QST)",ROUND(F${firstFutureRow}-C${firstFutureRow}-D${firstFutureRow},2),IF(G${firstFutureRow}="Ontario(GST/HST)",0,"N/A"))))`]];
transactions.getRange(`C${firstFutureRow}:C1000`).fillDown();
transactions.getRange(`D${firstFutureRow}:D1000`).fillDown();
transactions.getRange(`E${firstFutureRow}:E1000`).fillDown();

const validation = workbook.worksheets.getItem("Validation List");
validation.getRange("A21").values = [["5.16-Meals and Entertainment"]];
validation.getRange("A21").copyFrom(validation.getRange("A20"), "all");
validation.getRange("A21").values = [["5.16-Meals and Entertainment"]];

const pnl = workbook.worksheets.getItem("Profit and Loss Statement");
pnl.getRange("A2:B4").clear({ applyTo: "contents" });
pnl.getRange("A2:A4").values = [["Sales Revenue"], [null], ["Total"]];
pnl.getRange("B2").formulas = [["=SUMIF('Transactions'!$H$2:$H$1000,\"4.1- Sales Revenue(contact)\",'Transactions'!$C$2:$C$1000)"]];
pnl.getRange("B4").formulas = [["=B2"]];
const expenseCategories = [
  "5.13-Advertising",
  "5.2-Bank Charges and Interest",
  "5.3-Insurance",
  "5.16-Meals and Entertainment",
  "5.5-Licenses and Dues",
  "5.6-Office Expenses",
  "5.7-Accounting",
  "5.17-Professional Fees",
  "5.8-Rent",
  "5.18-Repairs and Maintenance",
  "5.9-Memebership and Subscriptions",
  "5.4-Subcontractors",
  "5.10-Telephone and Internet",
  "5.11-Utilities",
  "5.12-Vehicle Expenses",
  "5.19-Wages and Benefits",
  "5.15-Other Expenses",
];
pnl.getRange("B7:B23").formulas = expenseCategories.map((category) => [
  `=SUMIF('Transactions'!$H$2:$H$1000,"${category}",'Transactions'!$C$2:$C$1000)`,
]);
pnl.getRange("B24").formulas = [["=SUM(B7:B23)"]];
pnl.getRange("E2").formulas = [["=B4-B24"]];
pnl.getRange("D2").values = [["Profit before CCA"]];
pnl.getRange("D4:E4").copyFrom(pnl.getRange("D2:E2"), "all");
pnl.getRange("D4").values = [["Capital assets (not expensed)"]];
pnl.getRange("E4").formulas = [["=SUMIF('Transactions'!$H$2:$H$1000,\"1.4-Assets-Computer\",'Transactions'!$C$2:$C$1000)"]];
pnl.getRange("D6:E6").copyFrom(pnl.getRange("D2:E2"), "all");
pnl.getRange("D6:E6").values = [["Shareholder loan — amount you owe company", null]];
pnl.getRange("D6:E6").merge();
pnl.getRange("D6:E6").format.fill = "#6D9EEB";
pnl.getRange("D6:E6").format.font = { bold: true, color: "#000000" };
pnl.getRange("D7:D10").values = [[
  "Company-paid personal amounts",
], [
  "Less: amounts you paid for company",
], [
  "Net amount you owe the company",
], [
  "Balance as of 2026-07-10",
]];
pnl.getRange("E7:E8").values = [[24988.30], [-5764.90]];
pnl.getRange("E9").formulas = [["=SUM(E7:E8)"]];
pnl.getRange("D9:E9").format.font = { bold: true };
pnl.getRange("D9:E9").format.borders = { bottom: { style: "double", color: "#000000" } };
pnl.getRange("A1:A24").format.columnWidth = 34;
pnl.getRange("D1:D24").format.columnWidth = 42;
pnl.getRange("E1:E24").format.columnWidth = 16;
pnl.getRange("B2:B24").format.numberFormat = "$#,##0.00";
pnl.getRange("E2:E9").format.numberFormat = "$#,##0.00;[Red]($#,##0.00);-";

const keyCheck = await workbook.inspect({
  kind: "table",
  range: `Transactions!A1:H${rows.length + 1}`,
  include: "values,formulas",
  tableMaxRows: 45,
  tableMaxCols: 8,
  maxChars: 18000,
});
console.log(keyCheck.ndjson);
const pnlCheck = await workbook.inspect({
  kind: "table",
  range: "Profit and Loss Statement!A1:E24",
  include: "values,formulas",
  tableMaxRows: 24,
  tableMaxCols: 5,
  maxChars: 8000,
});
console.log(pnlCheck.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

for (const [sheetName, range] of [
  ["WELCOME!", "B1:E15"],
  ["Transactions", `A1:H${rows.length + 3}`],
  ["Profit and Loss Statement", "A1:E24"],
  ["Validation List", "A1:C28"],
  ["validation list (2)", "A1:D3"],
]) {
  const preview = await workbook.render({ sheetName, range, scale: 1.5, format: "png" });
  const safeName = sheetName.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "");
  await fs.writeFile(`${outputDir}/final_${safeName}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const exported = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const exportedTransactions = exported.worksheets.getItem("Transactions");
const exportedPnl = exported.worksheets.getItem("Profit and Loss Statement");
console.log(JSON.stringify({
  exportedFormulaRows2to45: exportedTransactions.getRange("C2:E45").formulas,
  exportedTaxValidation: exportedTransactions.getRange("G2:G1000").dataValidation,
  exportedCategoryValidation: exportedTransactions.getRange("H2:H1000").dataValidation,
  exportedRows2to45: exportedTransactions.getRange("A2:H45").values,
  exportedPnl: exportedPnl.getRange("A1:E24").values,
  outputPath,
  rowCount: rows.length,
}));

const recalculatedPath = `/tmp/comptabilite-recalc/${outputPath.split("/").at(-1)}`;
try {
  const recalculated = await SpreadsheetFile.importXlsx(await FileBlob.load(recalculatedPath));
  console.log(JSON.stringify({
    recalculatedPnl: recalculated.worksheets.getItem("Profit and Loss Statement").getRange("A1:E24").values,
    recalculatedLaptopRow: recalculated.worksheets.getItem("Transactions").getRange("A6:H6").values,
  }));
} catch (error) {
  console.log(JSON.stringify({ recalculationInspectionSkipped: error.message }));
}
