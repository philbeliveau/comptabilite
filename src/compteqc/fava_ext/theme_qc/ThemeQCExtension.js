// @ts-check
// Theme Quebec pour CompteQC - Injecte CSS global + branding

const THEME_CSS = `
/* ===== Quebec Color Palette ===== */
:root {
  --qc-blue: #003DA5;
  --qc-blue-light: #1A5BBF;
  --qc-blue-lighter: #E8EFF8;
  --qc-blue-dark: #002B75;
  --qc-white: #FFFFFF;
  --qc-surface: #F4F7FA;
  --qc-success: #2E7D32;
  --qc-success-bg: #E8F5E9;
  --qc-warning: #E65100;
  --qc-warning-bg: #FFF3E0;
  --qc-error: #C62828;
  --qc-error-bg: #FFEBEE;
  --qc-amber: #F9A825;
  --qc-amber-bg: #FFF8E1;
  --qc-muted: #64748B;
  --qc-border: #E2E8F0;
  --qc-shadow: 0 1px 3px rgba(0, 61, 165, 0.08), 0 1px 2px rgba(0, 61, 165, 0.06);
  --qc-shadow-md: 0 4px 6px rgba(0, 61, 165, 0.07), 0 2px 4px rgba(0, 61, 165, 0.06);

  /* Override Fava variables */
  --header-background: var(--qc-blue);
  --header-color: var(--qc-white);
  --link-color: var(--qc-blue-light);
  --sidebar-background: var(--qc-surface);
  --sidebar-border: var(--qc-border);
  --table-header-background: var(--qc-blue-lighter);
  --table-header-text: var(--qc-blue-dark);
  --button-background: var(--qc-blue);
  --button-color: var(--qc-white);
}

/* ===== Fava Header Override ===== */
header {
  background: var(--qc-blue) !important;
}

header a, header .links a {
  color: var(--qc-white) !important;
}

/* ===== CompteQC Brand Strip ===== */
#cqc-brand-strip {
  background: linear-gradient(135deg, var(--qc-blue-dark) 0%, var(--qc-blue) 100%);
  color: var(--qc-white);
  padding: 6px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.85em;
  border-bottom: 2px solid rgba(255, 255, 255, 0.15);
}

#cqc-brand-strip .cqc-fleur {
  font-size: 1.3em;
  opacity: 0.9;
}

#cqc-brand-strip .cqc-name {
  font-weight: 600;
  letter-spacing: 0.3px;
}

#cqc-brand-strip .cqc-sep {
  opacity: 0.4;
  margin: 0 4px;
}

#cqc-brand-strip .cqc-app {
  opacity: 0.8;
  font-size: 0.92em;
}

/* ===== Sidebar ===== */
aside {
  background: var(--qc-surface) !important;
  border-right: 1px solid var(--qc-border) !important;
}

aside a {
  color: var(--qc-blue) !important;
}

aside a:hover {
  color: var(--qc-blue-light) !important;
  background: var(--qc-blue-lighter) !important;
}

/* ===== Card Component ===== */
.cqc-card {
  background: var(--qc-white);
  border: 1px solid var(--qc-border);
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 20px;
  box-shadow: var(--qc-shadow);
}

.cqc-card-flush {
  background: var(--qc-white);
  border: 1px solid var(--qc-border);
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: var(--qc-shadow);
  overflow: hidden;
}

/* ===== Section Title ===== */
.cqc-section-title {
  font-size: 1.1em;
  font-weight: 600;
  color: var(--qc-blue-dark);
  margin: 0 0 16px 0;
  padding-left: 12px;
  border-left: 3px solid var(--qc-blue);
}

/* ===== Page Title ===== */
.cqc-page-header {
  margin-bottom: 24px;
}

.cqc-page-header h2 {
  font-size: 1.4em;
  font-weight: 700;
  color: var(--qc-blue-dark);
  margin: 0 0 6px 0;
}

.cqc-page-header .cqc-subtitle {
  color: var(--qc-muted);
  font-size: 0.92em;
}

/* ===== KPI Tiles ===== */
.cqc-kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.cqc-kpi {
  background: var(--qc-white);
  border: 1px solid var(--qc-border);
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: var(--qc-shadow);
}

.cqc-kpi-label {
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--qc-muted);
  margin-bottom: 4px;
}

.cqc-kpi-value {
  font-size: 1.5em;
  font-weight: 700;
  color: var(--qc-blue-dark);
  font-variant-numeric: tabular-nums;
}

.cqc-kpi-value.cqc-success { color: var(--qc-success); }
.cqc-kpi-value.cqc-error { color: var(--qc-error); }
.cqc-kpi-value.cqc-warning { color: var(--qc-warning); }

/* ===== Tables ===== */
.cqc-table {
  width: 100%;
  border-collapse: collapse;
}

.cqc-table th {
  background-color: var(--qc-blue-lighter);
  color: var(--qc-blue-dark);
  font-weight: 600;
  font-size: 0.85em;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  padding: 10px 14px;
  text-align: left;
  border-bottom: 2px solid var(--qc-blue);
}

.cqc-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--qc-border);
  text-align: left;
  font-size: 0.93em;
}

.cqc-table tbody tr:nth-child(even) {
  background-color: rgba(244, 247, 250, 0.5);
}

.cqc-table tbody tr:hover {
  background-color: var(--qc-blue-lighter);
}

.cqc-table .montant {
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-family: 'Fira Mono', monospace;
}

.cqc-table .sommaire-row {
  font-weight: 700;
  background-color: var(--qc-blue-lighter) !important;
}

.cqc-table .sommaire-row td {
  border-top: 2px solid var(--qc-blue);
  color: var(--qc-blue-dark);
}

/* ===== Badges ===== */
.cqc-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.8em;
  font-weight: 600;
  white-space: nowrap;
}

.cqc-badge-success {
  background: var(--qc-success-bg);
  color: var(--qc-success);
}

.cqc-badge-warning {
  background: var(--qc-amber-bg);
  color: #7C6900;
}

.cqc-badge-error {
  background: var(--qc-error-bg);
  color: var(--qc-error);
}

.cqc-badge-info {
  background: var(--qc-blue-lighter);
  color: var(--qc-blue);
}

.cqc-badge-muted {
  background: #F1F5F9;
  color: var(--qc-muted);
}

/* ===== Alerts ===== */
.cqc-alert {
  padding: 14px 18px;
  border-radius: 8px;
  margin-bottom: 16px;
  border-left: 4px solid;
  font-size: 0.93em;
}

.cqc-alert strong {
  display: block;
  margin-bottom: 4px;
}

.cqc-alert-success {
  background: var(--qc-success-bg);
  border-color: var(--qc-success);
  color: #1B5E20;
}

.cqc-alert-warning {
  background: var(--qc-warning-bg);
  border-color: var(--qc-warning);
  color: var(--qc-warning);
}

.cqc-alert-error {
  background: var(--qc-error-bg);
  border-color: var(--qc-error);
  color: #B71C1C;
}

.cqc-alert-info {
  background: var(--qc-blue-lighter);
  border-color: var(--qc-blue);
  color: var(--qc-blue-dark);
}

.cqc-alert-amber {
  background: var(--qc-amber-bg);
  border-color: var(--qc-amber);
  color: #7C6900;
}

/* ===== Buttons ===== */
.cqc-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 0.9em;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.cqc-btn-primary {
  background: var(--qc-blue);
  color: var(--qc-white);
  border-color: var(--qc-blue);
}

.cqc-btn-primary:hover {
  background: var(--qc-blue-light);
}

.cqc-btn-success {
  background: var(--qc-success);
  color: var(--qc-white);
  border-color: var(--qc-success);
}

.cqc-btn-success:hover {
  background: #256D29;
}

.cqc-btn-error {
  background: var(--qc-error);
  color: var(--qc-white);
  border-color: var(--qc-error);
}

.cqc-btn-error:hover {
  background: #A52222;
}

.cqc-btn-outline {
  background: var(--qc-white);
  color: var(--qc-blue);
  border-color: var(--qc-border);
}

.cqc-btn-outline:hover {
  border-color: var(--qc-blue);
  background: var(--qc-blue-lighter);
}

/* ===== Actions Bar ===== */
.cqc-actions-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--qc-surface);
  border-radius: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

/* ===== Solde Box (shareholder loan) ===== */
.cqc-solde-box {
  background: linear-gradient(135deg, var(--qc-blue) 0%, var(--qc-blue-light) 100%);
  color: var(--qc-white);
  padding: 24px 28px;
  border-radius: 10px;
  margin-bottom: 20px;
}

.cqc-solde-montant {
  font-size: 2em;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.cqc-solde-direction {
  opacity: 0.85;
  margin-top: 4px;
  font-size: 0.95em;
}

/* ===== Dropzone ===== */
.cqc-dropzone {
  min-height: 180px;
  border: 3px dashed var(--qc-border);
  border-radius: 12px;
  background: var(--qc-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  margin: 16px 0;
  padding: 20px;
}

.cqc-dropzone:hover {
  border-color: var(--qc-blue);
  background: var(--qc-blue-lighter);
}

.cqc-dropzone.dragover {
  border-color: var(--qc-success);
  background: var(--qc-success-bg);
  border-style: solid;
}

.cqc-dropzone-text {
  text-align: center;
  color: var(--qc-muted);
  font-size: 1.05em;
}

.cqc-dropzone-text .icone {
  font-size: 2.5em;
  display: block;
  margin-bottom: 10px;
  color: var(--qc-blue);
}

/* ===== Placeholder Box ===== */
.cqc-placeholder {
  padding: 28px;
  background: var(--qc-blue-lighter);
  border: 2px dashed var(--qc-blue);
  border-radius: 10px;
  margin: 20px 0;
}

.cqc-placeholder h3 {
  color: var(--qc-blue);
  margin-top: 0;
  font-size: 1.1em;
}

.cqc-placeholder ul {
  margin: 12px 0;
  padding-left: 20px;
}

.cqc-placeholder li {
  margin: 6px 0;
  color: var(--qc-blue-dark);
}

/* ===== Format Tags ===== */
.cqc-tag {
  display: inline-block;
  padding: 4px 12px;
  background: var(--qc-white);
  border: 1px solid var(--qc-blue);
  border-radius: 4px;
  margin-right: 8px;
  color: var(--qc-blue);
  font-size: 0.85em;
  font-weight: 600;
}

/* ===== Source Tag ===== */
.cqc-source-tag {
  display: block;
  font-size: 0.75em;
  color: var(--qc-muted);
  margin-top: 2px;
}

/* ===== Gros montant ===== */
.cqc-gros-montant {
  font-weight: 700;
  color: var(--qc-error);
}

.cqc-gros-montant::after {
  content: " \\26A0";
}

/* ===== Color utilities ===== */
.cqc-positif { color: var(--qc-error); }
.cqc-negatif { color: var(--qc-success); }

/* ===== Progress Bar ===== */
.cqc-progress {
  height: 6px;
  background: var(--qc-border);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 4px;
}

.cqc-progress-bar {
  height: 100%;
  background: var(--qc-blue);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.cqc-progress-bar.cqc-progress-full {
  background: var(--qc-success);
}

/* ===== Forms ===== */
.cqc-input {
  padding: 7px 12px;
  border: 1px solid var(--qc-border);
  border-radius: 6px;
  font-size: 0.9em;
  transition: border-color 0.15s ease;
}

.cqc-input:focus {
  outline: none;
  border-color: var(--qc-blue);
  box-shadow: 0 0 0 3px rgba(0, 61, 165, 0.1);
}

.cqc-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9em;
  color: var(--qc-muted);
}

/* ===== Empty State ===== */
.cqc-empty {
  text-align: center;
  padding: 32px;
  color: var(--qc-muted);
  font-style: italic;
}

/* ===== Note CPA ===== */
.cqc-note-cpa {
  padding: 12px 16px;
  background: var(--qc-amber-bg);
  border-left: 4px solid var(--qc-amber);
  border-radius: 6px;
  font-size: 0.9em;
  color: #7C6900;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .cqc-kpi-row {
    grid-template-columns: 1fr 1fr;
  }
  .cqc-actions-bar {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 480px) {
  .cqc-kpi-row {
    grid-template-columns: 1fr;
  }
}
`;

let styleInjected = false;
let brandInjected = false;

function injectStyle() {
  if (styleInjected) return;
  const existing = document.getElementById("cqc-theme-css");
  if (existing) { styleInjected = true; return; }

  const style = document.createElement("style");
  style.id = "cqc-theme-css";
  style.textContent = THEME_CSS;
  document.head.appendChild(style);
  styleInjected = true;
}

function injectBrand() {
  if (brandInjected) return;
  if (document.getElementById("cqc-brand-strip")) { brandInjected = true; return; }

  const header = document.querySelector("header");
  if (!header) return;

  const strip = document.createElement("div");
  strip.id = "cqc-brand-strip";
  strip.innerHTML = [
    '<span class="cqc-fleur">\u269C</span>',
    '<span class="cqc-name">Philippe Beliveau</span>',
    '<span class="cqc-sep">|</span>',
    '<span class="cqc-app">CompteQC</span>',
  ].join("");

  header.insertAdjacentElement("afterend", strip);
  brandInjected = true;
}

/** @type import("fava").ExtensionModule */
export default {
  init() {
    injectStyle();
    injectBrand();
  },
  onPageLoad() {
    injectStyle();
    injectBrand();
  },
};
