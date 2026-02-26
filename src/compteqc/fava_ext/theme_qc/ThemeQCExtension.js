// @ts-check
// Theme Quebec pour CompteQC — Modern UI rework
// Couleur primaire tirée du drapeau du Québec (#003DA5)

const THEME_CSS = `
/* ===== Quebec Color Palette (flag-coherent) ===== */
:root {
  /* Core Quebec blue from the fleurdelise */
  --qc-blue: #003DA5;
  --qc-blue-light: #1A5BBF;
  --qc-blue-lighter: #EDF2FB;
  --qc-blue-dark: #002B75;
  --qc-blue-deep: #001840;
  --qc-white: #FFFFFF;

  /* Surfaces */
  --qc-surface: #F8FAFC;
  --qc-surface-raised: #FFFFFF;
  --qc-surface-sidebar: #0A1628;

  /* Semantic */
  --qc-success: #16A34A;
  --qc-success-bg: #F0FDF4;
  --qc-warning: #EA580C;
  --qc-warning-bg: #FFF7ED;
  --qc-error: #DC2626;
  --qc-error-bg: #FEF2F2;
  --qc-amber: #D97706;
  --qc-amber-bg: #FFFBEB;
  --qc-info-bg: var(--qc-blue-lighter);

  /* Neutrals */
  --qc-text: #1E293B;
  --qc-text-secondary: #64748B;
  --qc-muted: #94A3B8;
  --qc-border: #E2E8F0;
  --qc-border-light: #F1F5F9;

  /* Elevation */
  --qc-shadow-xs: 0 1px 2px rgba(0,0,0,0.04);
  --qc-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --qc-shadow-md: 0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04);
  --qc-shadow-lg: 0 8px 24px rgba(0,0,0,0.08), 0 4px 8px rgba(0,0,0,0.04);

  /* Radii */
  --qc-radius: 12px;
  --qc-radius-sm: 8px;
  --qc-radius-lg: 16px;

  /* Transitions */
  --qc-transition: 180ms cubic-bezier(0.4, 0, 0.2, 1);
  --qc-transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1);

  /* === Fava CSS Custom Property Overrides === */
  /* These replace ~80% of forced-priority declarations by reassigning Fava's own variables */
  --header-background: var(--qc-blue);
  --header-color: var(--qc-white);
  --link-color: var(--qc-blue);
  --link-hover-color: var(--qc-blue-light);
  --sidebar-background: var(--qc-surface-sidebar);
  --sidebar-text: rgba(255, 255, 255, 1);
  --sidebar-border: transparent;
  --background: var(--qc-surface);
  --text-color: var(--qc-text);
  --secondary-text: var(--qc-text-secondary);
  --heading-color: var(--qc-blue);
  --border: var(--qc-border);
  --table-header-background: var(--qc-blue-lighter);
  --table-header-text: var(--qc-blue-dark);
  --table-border: var(--qc-border-light);
  --button-background: var(--qc-blue);
  --button-color: var(--qc-white);
  --button-hover-background: var(--qc-blue-light);
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  --font-size: 14px;

  /* === CompteQC Type Scale (Inter) === */
  /* Based on 1.200 minor third ratio from 16px base */
  --cqc-font-xs: 0.6875rem;    /* 11px -- table headers, labels */
  --cqc-font-sm: 0.8125rem;    /* 13px -- secondary text, badges */
  --cqc-font-base: 0.875rem;   /* 14px -- body text, table cells */
  --cqc-font-md: 1rem;         /* 16px -- prominent body, card text */
  --cqc-font-lg: 1.25rem;      /* 20px -- section headings */
  --cqc-font-xl: 1.5rem;       /* 24px -- page titles */
  --cqc-font-2xl: 2rem;        /* 32px -- KPI values */
  --cqc-font-3xl: 2.5rem;      /* 40px -- hero numbers */

  --cqc-weight-normal: 400;
  --cqc-weight-medium: 500;
  --cqc-weight-semibold: 600;
  --cqc-weight-bold: 700;

  --cqc-leading-tight: 1.2;
  --cqc-leading-normal: 1.5;
  --cqc-leading-relaxed: 1.75;
}

/* ===== Global Reset ===== */
body, article, aside, header,
.flex-table, .flex-table span, .flex-table a, .flex-table p,
ol, ul, li, p, span, div,
table, th, td, tr,
input, select, textarea, button,
label, legend, fieldset,
h1, h2, h3, h4, h5, h6 {
  /* OVERRIDE: Global font -- Fava has no --font-family variable on all elements */
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

article {
  background: var(--qc-surface);
}

/* ===== Fava Header ===== */
header {
  background: var(--header-background);
  box-shadow: 0 2px 8px rgba(0, 61, 165, 0.25);
  position: relative;
  z-index: 100;
}

/* Quebec flag logo in header */
header img#cqc-header-logo {
  height: 28px;
  width: auto;
  border-radius: 3px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  object-fit: contain;
}

header a, header .links a {
  color: rgba(255, 255, 255, 0.9);
  transition: color var(--qc-transition);
}

header a:hover, header .links a:hover {
  color: #FFFFFF;
}

header h1 {
  font-weight: 600;
  letter-spacing: -0.01em;
}

header h1 strong {
  font-weight: 700;
}

/* Header filter inputs */
header input, header select {
  border-radius: var(--qc-radius-sm);
  border: 1px solid rgba(255,255,255,0.2);
  background: rgba(255,255,255,0.1);
  color: white;
  backdrop-filter: blur(4px);
  transition: all var(--qc-transition);
  font-family: 'Inter', sans-serif;
}

header input:focus, header select:focus {
  background: rgba(255,255,255,0.18);
  border-color: rgba(255,255,255,0.4);
  outline: none;
  box-shadow: 0 0 0 3px rgba(255,255,255,0.1);
}

header input::placeholder {
  color: rgba(255,255,255,0.5);
}

/* ===== CompteQC Brand Strip ===== */
/* OVERRIDE: Svelte-scoped -- brand strip hidden by default, shown by JS injection */
#cqc-brand-strip { display: none !important; }
#cqc-brand-strip {
  background: linear-gradient(180deg, rgba(0,61,165,0.6) 0%, var(--qc-surface-sidebar) 100%);
  color: #ffffff;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.8em;
  font-family: 'Inter', sans-serif;
  letter-spacing: 0.02em;
  border-bottom: 2px solid rgba(0, 61, 165, 0.3);
  border-top: 1px solid rgba(255,255,255,0.08);
  transition: all var(--qc-transition);
}

#cqc-brand-strip:hover {
  background: linear-gradient(180deg, rgba(0,61,165,0.75) 0%, var(--qc-surface-sidebar) 100%);
  border-bottom-color: rgba(0, 61, 165, 0.5);
}

#cqc-brand-strip .cqc-fleur {
  font-size: 1.3em;
  color: #ffffff;
  opacity: 0.95;
}

#cqc-brand-strip .cqc-name {
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 0.02em;
}

#cqc-brand-strip .cqc-sep {
  opacity: 0.3;
  margin: 0 2px;
  color: #ffffff;
}

#cqc-brand-strip .cqc-app {
  color: #ffffff;
  font-size: 0.92em;
  font-weight: 500;
  opacity: 0.75;
}

/* ===== Footer ===== */
/* OVERRIDE: Svelte-scoped -- Fava footer hidden to match CompteQC branding */
footer { display: none !important; }

/* ===== Dark Sidebar ===== */
/* OVERRIDE: Svelte-scoped -- sidebar has Fava inline styles that must be overridden */
aside {
  background: var(--qc-surface-sidebar) !important;
  border-right: none;
  box-shadow: 1px 0 0 rgba(255,255,255,0.04);
  padding-top: 8px;
  width: 310px !important;
  min-width: 310px !important;
}

aside ul {
  padding: 4px 8px;
}

aside li {
  margin: 1px 0;
}

aside a {
  color: var(--sidebar-text, rgba(255, 255, 255, 1));
  font-size: 0.88em;
  font-weight: 450;
  padding: 7px 12px;
  border-radius: var(--qc-radius-sm);
  display: block;
  transition: all var(--qc-transition);
  text-decoration: none;
  letter-spacing: 0.01em;
}

aside a:hover {
  color: rgba(255, 255, 255, 0.95);
  background: rgba(255, 255, 255, 0.08);
}

/* Active sidebar link -- Fava uses class or aria */
aside li.selected a,
aside a[aria-current],
aside a.selected {
  color: #FFFFFF;
  background: rgba(0, 61, 165, 0.5);
  font-weight: 600;
}

/* Sidebar section separators */
aside ul + ul {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-top: 6px;
  padding-top: 6px;
}

/* Sidebar inputs */
aside input, aside select {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.7);
  border-radius: var(--qc-radius-sm);
  font-size: 0.85em;
  padding: 6px 10px;
  transition: all var(--qc-transition);
  font-family: 'Inter', sans-serif;
}

aside input:focus, aside select:focus {
  background: rgba(255,255,255,0.1);
  border-color: rgba(0, 61, 165, 0.6);
  outline: none;
}

aside input::placeholder {
  color: rgba(255,255,255,0.3);
}

/* ===== Main Content Area ===== */
article {
  padding: 28px 32px;
}

/* Fava native tables -- give them the modern treatment */
article table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.9em;
}

article table th {
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 0.78em;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--qc-text-secondary);
  background: var(--table-header-background);
  padding: 10px 14px;
  border-bottom: 2px solid var(--qc-border);
}

article table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--table-border);
  background: var(--qc-surface-raised);
  color: var(--qc-text);
  transition: background var(--qc-transition);
}

article table tbody tr:hover td {
  background: var(--qc-blue-lighter);
}

/* Fava links in content */
article a {
  color: var(--link-color);
  text-decoration: none;
  font-weight: 500;
  transition: color var(--qc-transition);
}

article a:hover {
  color: var(--link-hover-color);
}

/* Fava chart toggles / buttons row */
article .headerline {
  margin-bottom: 20px;
}

/* ===== Card Component ===== */
.cqc-card {
  background: var(--qc-surface-raised);
  border: 1px solid var(--qc-border-light);
  border-radius: var(--qc-radius);
  padding: 22px 26px;
  margin-bottom: 20px;
  box-shadow: var(--qc-shadow);
  transition: box-shadow var(--qc-transition-slow);
}

.cqc-card:hover {
  box-shadow: var(--qc-shadow-md);
}

.cqc-card-flush {
  background: var(--qc-surface-raised);
  border: 1px solid var(--qc-border-light);
  border-radius: var(--qc-radius);
  margin-bottom: 20px;
  box-shadow: var(--qc-shadow);
  overflow: hidden;
  transition: box-shadow var(--qc-transition-slow);
}

.cqc-card-flush:hover {
  box-shadow: var(--qc-shadow-md);
}

/* ===== Section Title ===== */
.cqc-section-title {
  font-size: var(--cqc-font-md);
  font-weight: var(--cqc-weight-semibold);
  color: var(--qc-text);
  margin: 0 0 16px 0;
  padding-left: 14px;
  border-left: 3px solid var(--qc-blue);
  letter-spacing: -0.01em;
}

/* Section title inside card-flush: add top/side padding */
.cqc-card-flush > .cqc-section-title {
  padding: 16px 24px 0;
  font-weight: 600;
  border-left: none;
  margin-bottom: 0;
}

/* ===== Page Header ===== */
.cqc-page-header {
  margin-bottom: 28px;
}

.cqc-page-header h2 {
  font-size: var(--cqc-font-xl);
  font-weight: var(--cqc-weight-bold);
  color: var(--qc-text);
  margin: 0 0 6px 0;
  letter-spacing: -0.02em;
}

.cqc-page-header .cqc-subtitle {
  color: var(--qc-text-secondary);
  font-size: 0.9em;
  font-weight: 450;
}

/* ===== KPI Tiles ===== */
.cqc-kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}

.cqc-kpi {
  background: var(--qc-surface-raised);
  border: 1px solid var(--qc-border-light);
  border-radius: var(--qc-radius);
  padding: 20px 22px;
  box-shadow: var(--qc-shadow);
  position: relative;
  overflow: hidden;
  transition: all var(--qc-transition-slow);
}

.cqc-kpi::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--qc-blue);
  opacity: 0.7;
  transition: opacity var(--qc-transition);
}

.cqc-kpi:hover {
  box-shadow: var(--qc-shadow-md);
  transform: translateY(-1px);
}

.cqc-kpi:hover::before {
  opacity: 1;
}

.cqc-kpi-label {
  font-size: 0.75em;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--qc-text-secondary);
  margin-bottom: 6px;
  font-weight: 500;
}

.cqc-kpi-value {
  font-size: var(--cqc-font-2xl);
  font-weight: var(--cqc-weight-bold);
  color: var(--qc-text);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: var(--cqc-leading-tight);
}

.cqc-kpi-value.cqc-success { color: var(--qc-success); }
.cqc-kpi-value.cqc-error { color: var(--qc-error); }
.cqc-kpi-value.cqc-warning { color: var(--qc-warning); }

/* ===== Tables ===== */
.cqc-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.cqc-table thead th {
  background-color: var(--qc-blue-lighter);
  color: var(--qc-blue-dark);
  font-weight: 700;
  font-size: 0.76em;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 12px 16px;
  text-align: left;
  border-bottom: 2px solid var(--qc-blue);
  position: sticky;
  top: 0;
  z-index: 1;
  white-space: nowrap;
}

.cqc-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--qc-border-light);
  background: var(--qc-surface-raised);
  text-align: left;
  font-size: var(--cqc-font-base);
  line-height: var(--cqc-leading-normal);
  color: var(--qc-text);
  vertical-align: middle;
  transition: background-color var(--qc-transition);
}

.cqc-table tbody tr {
  background: var(--qc-surface-raised);
  transition: background-color var(--qc-transition);
}

.cqc-table tbody tr:hover {
  background-color: var(--qc-blue-lighter);
}

.cqc-table tbody tr:hover td {
  background-color: var(--qc-blue-lighter) !important;
  transition: background-color 150ms ease;
}

/* Subtle zebra striping */
.cqc-table tbody tr:nth-child(even) {
  background-color: rgba(0, 61, 165, 0.015);
}

/* Last row: clean bottom */
.cqc-table tbody tr:last-child td {
  border-bottom: none;
}

/* === Tabular numbers for financial data === */
.cqc-table .montant,
.cqc-table td:last-child,
.cqc-kpi-value,
[data-value] {
  font-variant-numeric: tabular-nums;
}

/* Negative amounts styling */
.cqc-table .montant-negatif {
  color: var(--qc-error, #dc3545);
}

/* Right-align money columns */
.cqc-table .montant {
  text-align: right;
  font-weight: var(--cqc-weight-medium);
  letter-spacing: -0.01em;
}

.cqc-table .sommaire-row {
  font-weight: 700;
  background-color: var(--qc-surface);
}

.cqc-table .sommaire-row td {
  font-weight: 700;
  border-top: 2px solid var(--qc-blue);
  background-color: var(--qc-blue-lighter) !important;
  color: var(--qc-text);
  padding-top: 14px;
  padding-bottom: 14px;
}

/* Focused row for keyboard navigation (prep for 08-02) */
.cqc-table tbody tr.cqc-row-focused td {
  background-color: rgba(0, 61, 165, 0.08) !important;
  outline: 2px solid var(--qc-blue);
  outline-offset: -2px;
}

/* ===== Table Utility Classes ===== */
.cqc-text-muted {
  font-size: 0.85em;
  color: var(--qc-muted, #64748B);
}

.cqc-cell-flex {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cqc-table .cqc-col-checkbox {
  width: 40px;
  text-align: center;
}

/* ===== Badges ===== */
.cqc-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.78em;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: 0.01em;
  transition: all var(--qc-transition);
}

.cqc-badge-success {
  background: var(--qc-success-bg);
  color: var(--qc-success);
}

.cqc-badge-warning {
  background: var(--qc-amber-bg);
  color: var(--qc-amber);
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
  background: var(--qc-border-light);
  color: var(--qc-muted);
}

/* ===== Alerts ===== */
.cqc-alert {
  padding: 16px 20px;
  border-radius: var(--qc-radius);
  margin-bottom: 16px;
  border-left: 4px solid;
  font-size: 0.9em;
  line-height: 1.5;
}

.cqc-alert strong {
  display: block;
  margin-bottom: 4px;
  font-weight: 600;
}

.cqc-alert-success {
  background: var(--qc-success-bg);
  border-color: var(--qc-success);
  color: #15803D;
}

.cqc-alert-warning {
  background: var(--qc-warning-bg);
  border-color: var(--qc-warning);
  color: #C2410C;
}

.cqc-alert-error {
  background: var(--qc-error-bg);
  border-color: var(--qc-error);
  color: #B91C1C;
}

.cqc-alert-info {
  background: var(--qc-blue-lighter);
  border-color: var(--qc-blue);
  color: var(--qc-blue-dark);
}

.cqc-alert-amber {
  background: var(--qc-amber-bg);
  border-color: var(--qc-amber);
  color: #92400E;
}

/* ===== Buttons ===== */
.cqc-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  border-radius: var(--qc-radius-sm);
  font-size: 0.88em;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--qc-transition);
  font-family: 'Inter', sans-serif;
  letter-spacing: 0.01em;
  line-height: 1.2;
}

.cqc-btn:active {
  transform: scale(0.97);
}

.cqc-btn-primary {
  background: var(--qc-blue);
  color: var(--qc-white);
  border-color: var(--qc-blue);
  box-shadow: 0 1px 2px rgba(0, 61, 165, 0.2);
}

.cqc-btn-primary:hover {
  background: var(--qc-blue-light);
  box-shadow: 0 2px 6px rgba(0, 61, 165, 0.25);
}

.cqc-btn-success {
  background: var(--qc-success);
  color: var(--qc-white);
  border-color: var(--qc-success);
  box-shadow: 0 1px 2px rgba(22, 163, 74, 0.2);
}

.cqc-btn-success:hover {
  background: #15803D;
  box-shadow: 0 2px 6px rgba(22, 163, 74, 0.25);
}

.cqc-btn-error {
  background: var(--qc-error);
  color: var(--qc-white);
  border-color: var(--qc-error);
  box-shadow: 0 1px 2px rgba(220, 38, 38, 0.2);
}

.cqc-btn-error:hover {
  background: #B91C1C;
  box-shadow: 0 2px 6px rgba(220, 38, 38, 0.25);
}

.cqc-btn-outline {
  background: var(--qc-white);
  color: var(--qc-text);
  border-color: var(--qc-border);
  box-shadow: var(--qc-shadow-xs);
}

.cqc-btn-outline:hover {
  border-color: var(--qc-blue);
  color: var(--qc-blue);
  background: var(--qc-blue-lighter);
}

/* ===== Actions Bar ===== */
.cqc-actions-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: var(--qc-surface-raised);
  border: 1px solid var(--qc-border-light);
  border-radius: var(--qc-radius);
  margin-bottom: 16px;
  flex-wrap: wrap;
  box-shadow: var(--qc-shadow-xs);
}

/* ===== Solde Box (shareholder loan) ===== */
.cqc-solde-box {
  background: linear-gradient(135deg, var(--qc-blue-dark) 0%, var(--qc-blue) 50%, var(--qc-blue-light) 100%);
  color: var(--qc-white);
  padding: 28px 32px;
  border-radius: var(--qc-radius-lg);
  margin-bottom: 24px;
  box-shadow: 0 4px 16px rgba(0, 61, 165, 0.25);
  position: relative;
  overflow: hidden;
}

.cqc-solde-box::after {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%);
  pointer-events: none;
}

.cqc-solde-montant {
  font-size: 2.2em;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.cqc-solde-direction {
  opacity: 0.8;
  margin-top: 6px;
  font-size: 0.95em;
  font-weight: 450;
}

/* ===== Dropzone ===== */
.cqc-dropzone {
  min-height: 180px;
  border: 2px dashed var(--qc-border);
  border-radius: var(--qc-radius-lg);
  background: var(--qc-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--qc-transition-slow);
  margin: 16px 0;
  padding: 24px;
}

.cqc-dropzone:hover {
  border-color: var(--qc-blue);
  background: var(--qc-blue-lighter);
  box-shadow: 0 0 0 4px rgba(0, 61, 165, 0.06);
}

@keyframes cqc-border-pulse {
  0%, 100% { border-color: var(--qc-blue); }
  50% { border-color: var(--qc-blue-light, #4a90d9); }
}

.cqc-dropzone.dragover {
  animation: cqc-border-pulse 1.2s ease-in-out infinite;
  border-style: solid;
  border-color: var(--qc-blue);
  background: var(--qc-blue-lighter);
  box-shadow: 0 0 16px rgba(0, 61, 165, 0.15);
}

.cqc-dropzone-text {
  text-align: center;
  color: var(--qc-text-secondary);
  font-size: 1em;
}

.cqc-dropzone-text .icone {
  font-size: 2.5em;
  display: block;
  margin-bottom: 10px;
  color: var(--qc-blue);
}

/* ===== Placeholder Box ===== */
.cqc-placeholder {
  padding: 32px;
  background: var(--qc-blue-lighter);
  border: 2px dashed rgba(0, 61, 165, 0.25);
  border-radius: var(--qc-radius-lg);
  margin: 20px 0;
}

.cqc-placeholder h3 {
  color: var(--qc-blue);
  margin-top: 0;
  font-size: var(--cqc-font-lg);
  font-weight: var(--cqc-weight-semibold);
}

.cqc-placeholder ul {
  margin: 12px 0;
  padding-left: 20px;
}

.cqc-placeholder li {
  margin: 6px 0;
  color: var(--qc-blue-dark);
  font-size: 0.92em;
}

/* ===== Tags ===== */
.cqc-tag {
  display: inline-block;
  padding: 4px 12px;
  background: var(--qc-blue-lighter);
  border: 1px solid rgba(0, 61, 165, 0.15);
  border-radius: 20px;
  margin-right: 6px;
  color: var(--qc-blue);
  font-size: 0.82em;
  font-weight: 600;
}

/* ===== Source Tag ===== */
.cqc-source-tag {
  display: block;
  font-size: 0.73em;
  color: var(--qc-muted);
  margin-top: 2px;
  font-weight: 450;
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
  transition: width var(--qc-transition-slow);
}

.cqc-progress-bar.cqc-progress-full {
  background: var(--qc-success);
}

/* ===== Upload Progress Bar ===== */
.cqc-upload-progress {
  width: 100%;
  height: 28px;
  background: var(--qc-surface);
  border-radius: var(--qc-radius-sm);
  overflow: hidden;
  margin: 16px 0;
  border: 1px solid var(--qc-border);
}

.cqc-upload-progress-bar {
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, var(--qc-blue), var(--qc-blue-light, #4a90d9));
  border-radius: var(--qc-radius-sm);
  transition: width 150ms ease-out;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cqc-upload-progress-text {
  color: #fff;
  font-size: var(--cqc-font-sm, 0.875rem);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.cqc-upload-status {
  text-align: center;
  padding: 12px;
  color: var(--qc-text-secondary);
  font-size: var(--cqc-font-sm, 0.875rem);
}

@media (prefers-reduced-motion: reduce) {
  .cqc-upload-progress-bar {
    transition: none;
  }
  .cqc-dropzone.dragover {
    animation: none;
  }
}

.cqc-upload-queue-status {
  text-align: center;
  padding: 8px;
  color: var(--qc-text-secondary);
  font-size: var(--cqc-font-sm, 0.875rem);
  font-weight: 500;
}

/* ===== File Previews ===== */
.cqc-preview-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin: 16px 0;
}

.cqc-preview-item {
  width: 120px;
  text-align: center;
  padding: 12px;
  background: var(--qc-surface);
  border: 1px solid var(--qc-border);
  border-radius: var(--qc-radius-md, 8px);
  transition: box-shadow var(--qc-transition-fast, 150ms);
}

.cqc-preview-item:hover {
  box-shadow: var(--qc-shadow-md, 0 4px 12px rgba(0,0,0,0.08));
}

.cqc-preview-thumb {
  width: 96px;
  height: 96px;
  object-fit: cover;
  border-radius: var(--qc-radius-sm, 4px);
  display: block;
  margin: 0 auto 8px;
}

.cqc-preview-icon {
  font-size: 3em;
  display: block;
  margin-bottom: 8px;
  color: var(--qc-blue);
}

.cqc-preview-name {
  display: block;
  font-size: var(--cqc-font-xs, 0.75rem);
  color: var(--qc-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.cqc-preview-badge {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  background: var(--qc-blue-lighter);
  color: var(--qc-blue-dark, #002d7a);
  border-radius: 12px;
  font-size: var(--cqc-font-xs, 0.75rem);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

/* ===== Forms ===== */
.cqc-input {
  padding: 9px 14px;
  border: 1px solid var(--qc-border);
  border-radius: var(--qc-radius-sm);
  font-size: 0.9em;
  font-family: 'Inter', sans-serif;
  color: var(--qc-text);
  background: var(--qc-white);
  transition: all var(--qc-transition);
}

.cqc-input:focus {
  outline: none;
  border-color: var(--qc-blue);
  box-shadow: 0 0 0 3px rgba(0, 61, 165, 0.08);
}

.cqc-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.88em;
  color: var(--qc-text-secondary);
  font-weight: 500;
}

/* ===== Empty State ===== */
.cqc-empty {
  text-align: center;
  padding: 40px 32px;
  color: var(--qc-muted);
  font-size: 0.95em;
}

/* ===== Note CPA ===== */
.cqc-note-cpa {
  padding: 14px 18px;
  background: var(--qc-amber-bg);
  border-left: 4px solid var(--qc-amber);
  border-radius: var(--qc-radius-sm);
  font-size: 0.88em;
  color: #92400E;
  line-height: 1.5;
}

/* ===== Scrollbar (sidebar) ===== */
aside::-webkit-scrollbar {
  width: 4px;
}

aside::-webkit-scrollbar-track {
  background: transparent;
}

aside::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
}

aside::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.2);
}

/* ===== Fava overrides for native components ===== */
/* Fava uses svelte components -- style their containers */

/* Tree table / flex-table (income_statement, balance_sheet, trial_balance) */
/* Fava 1.30+ uses ol.flex-table.tree-table-new, NOT <table> */
article .tree-table td {
  font-size: 0.9em;
}

/* OVERRIDE: Svelte-scoped -- overrides Svelte-injected rgb(64,64,64) inline color */
article .flex-table {
  color: var(--qc-text) !important;
  font-family: 'Inter', sans-serif;
}

/* OVERRIDE: Svelte-scoped -- Svelte injects inline color on .num spans */
article .flex-table .num {
  color: var(--qc-text) !important;
  font-variant-numeric: tabular-nums;
}

/* Dimmed = propagated sums -- still readable but clearly secondary */
/* OVERRIDE: Svelte-scoped -- Svelte sets inline color and opacity on dimmed elements */
article .flex-table .num.dimmed {
  color: var(--qc-text-secondary) !important;
  opacity: 1 !important;
}

/* Account name links in flex-table */
/* OVERRIDE: Svelte-scoped -- Svelte injects inline color on links */
article .flex-table a {
  color: var(--qc-blue) !important;
  font-weight: 500;
}

/* Row hover highlight for flex-table rows */
article .flex-table li:hover > p {
  background: var(--qc-blue-lighter);
  border-radius: var(--qc-radius-sm);
}

/* Column header row (CAD / Other) */
article .flex-table li:first-child .num {
  color: var(--qc-blue-dark);
  font-weight: 600;
  font-size: 0.78em;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Fava buttons in toolbar */
article button, article .button {
  font-family: 'Inter', sans-serif;
  border-radius: var(--qc-radius-sm);
  transition: all var(--qc-transition);
}

/* Fava chart container */
article svg {
  border-radius: var(--qc-radius-sm);
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
  article {
    padding: 20px 16px;
  }
}

@media (max-width: 480px) {
  .cqc-kpi-row {
    grid-template-columns: 1fr;
  }
}

/* ===== Sidebar collapsible groups ===== */
.cqc-sidebar-group { margin: 2px 0; }
.cqc-sidebar-group-body { display: none; }
.cqc-sidebar-group.open > .cqc-sidebar-group-body { display: block; }
.cqc-sidebar-group-title {
  color: rgba(255,255,255,0.5);
  font-size: 0.72em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 8px 12px 4px 12px;
  cursor: pointer;
  user-select: none;
  transition: color var(--qc-transition);
  display: flex;
  align-items: center;
  gap: 6px;
}
.cqc-sidebar-group-title:hover { color: rgba(255,255,255,0.8); }
.cqc-sidebar-group-title::before {
  content: "\\25B8";
  flex-shrink: 0;
  transition: transform var(--qc-transition);
  font-size: 0.9em;
}
.cqc-sidebar-group.open > .cqc-sidebar-group-title::before {
  transform: rotate(90deg);
}
/* Remove old ul+ul separator since groups handle visual separation */
/* OVERRIDE: Svelte-scoped -- Fava sidebar navigation has inline border styles */
.cqc-sidebar-group ul.navigation { border-top: none !important; margin-top: 0; padding-top: 0; }

/* ===== Report intro blocks ===== */
.cqc-report-intro {
  margin-bottom: 24px;
  border-left: 4px solid var(--qc-blue);
  background: var(--qc-blue-lighter);
}
.cqc-report-intro h3 {
  margin: 0 0 8px 0;
  color: var(--qc-blue-dark);
  font-size: var(--cqc-font-lg);
  font-weight: var(--cqc-weight-semibold);
}
.cqc-report-intro p {
  margin: 6px 0;
  color: var(--qc-text);
  font-size: 0.9em;
  line-height: 1.6;
}

/* ===== Tooltip system ===== */
[data-tooltip] {
  cursor: help;
  text-decoration: underline dotted var(--qc-muted);
  text-underline-offset: 3px;
}

#cqc-tooltip-popup {
  position: fixed;
  z-index: 9999;
  background: var(--qc-surface-sidebar);
  color: #fff;
  padding: 10px 14px;
  border-radius: var(--qc-radius-sm);
  font-size: 0.82em;
  font-weight: 400;
  line-height: 1.5;
  max-width: 320px;
  box-shadow: var(--qc-shadow-lg);
  pointer-events: none;
  white-space: normal;
  text-align: left;
  opacity: 0;
  visibility: hidden;
  transition: opacity 150ms ease;
  font-family: 'Inter', sans-serif;
  transform: translateY(-100%) translateY(-8px);
}

#cqc-tooltip-popup.cqc-tooltip-visible {
  opacity: 1;
  visibility: visible;
}

/* === Chart containers === */
.cqc-chart-container {
  position: relative;
  width: 100%;
  height: 300px;
  padding: 16px;
}
/* OVERRIDE: Chart.js canvas -- Chart.js sets inline width/height that must be overridden for responsive sizing */
.cqc-chart-container canvas {
  width: 100% !important;
  height: 100% !important;
}

/* === Page entry animation === */
@keyframes cqc-page-enter {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.cqc-page-entering {
  animation: cqc-page-enter 200ms ease-out;
}

/* === KPI card staggered entrance === */
@keyframes cqc-fadeSlideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* === Confidence visualization === */
.cqc-confidence {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.cqc-confidence-bar {
  width: 48px;
  height: 6px;
  border-radius: 3px;
  background: var(--qc-border);
  overflow: hidden;
}
.cqc-confidence-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 300ms ease;
}
.cqc-confidence-pct {
  font-size: 0.78em;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  min-width: 32px;
}
.cqc-confidence-high .cqc-confidence-bar-fill { background: var(--qc-success); }
.cqc-confidence-high .cqc-confidence-pct { color: var(--qc-success); }
.cqc-confidence-medium .cqc-confidence-bar-fill { background: var(--qc-amber); }
.cqc-confidence-medium .cqc-confidence-pct { color: var(--qc-amber); }
.cqc-confidence-low .cqc-confidence-bar-fill { background: var(--qc-error); }
.cqc-confidence-low .cqc-confidence-pct { color: var(--qc-error); }

/* Row confidence borders */
.cqc-table tbody tr.cqc-row-high-confidence td:first-child {
  border-left: 3px solid var(--qc-success);
}
.cqc-table tbody tr.cqc-row-low-confidence td:first-child {
  border-left: 3px solid var(--qc-amber);
}

/* Keyboard shortcut hint */
.cqc-keyboard-hint {
  font-size: 0.8em;
  color: var(--qc-muted, #64748B);
  margin-top: 8px;
}
.cqc-keyboard-hint kbd {
  display: inline-block;
  padding: 2px 6px;
  font-size: 0.85em;
  font-family: 'Inter', monospace;
  background: var(--qc-surface-raised, #f8f9fa);
  border: 1px solid var(--qc-border, #d1d5db);
  border-radius: 4px;
  box-shadow: 0 1px 0 var(--qc-border, #d1d5db);
}

/* === Sidebar notification badge === */
.cqc-sidebar-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: var(--qc-error);
  color: #fff;
  font-size: 0.72em;
  font-weight: 700;
  margin-left: 8px;
  font-variant-numeric: tabular-nums;
}

/* === Reduced motion safety net === */
/* OVERRIDE: Accessibility -- must override all animations for users who prefer reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  .cqc-page-entering {
    animation: none;
  }
}
`;

let styleInjected = false;
let brandInjected = false;

function injectStyle() {
  if (styleInjected) return;
  const existing = document.getElementById("cqc-theme-css");
  if (existing) { styleInjected = true; return; }

  // Inject Google Fonts via <link> (not @import — @import inside dynamic <style> is unreliable)
  if (!document.getElementById("cqc-font-link")) {
    const link = document.createElement("link");
    link.id = "cqc-font-link";
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap";
    document.head.appendChild(link);
  }

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
    '<span class="cqc-sep">\u00B7</span>',
    '<span class="cqc-app">CompteQC</span>',
  ].join("");

  header.insertAdjacentElement("afterend", strip);
  brandInjected = true;
}

/**
 * Sidebar group definitions: each maps link text patterns to a French group name.
 * Order matters for display. The last group ("Extensions Québec") is the catch-all.
 */
const SIDEBAR_GROUPS = [
  {
    name: "Rapports financiers",
    patterns: ["Income Statement", "Balance Sheet", "Trial Balance", "Journal", "Profit and Loss"],
    open: true,
  },
  {
    name: "Données et documents",
    patterns: ["Holdings", "Commodities", "Documents", "Statistics", "Events"],
    open: false,
  },
  {
    name: "Outils",
    patterns: ["Editor", "Errors", "Import", "Query", "Options"],
    open: false,
  },
];

function reorganizeSidebar() {
  const aside = document.querySelector("aside");
  if (!aside || aside.dataset.cqcGrouped === "true") return;

  const navLists = aside.querySelectorAll("ul.navigation");
  if (navLists.length === 0) return;

  // Classify each <ul> into a group based on its link text content
  const grouped = new Map(); // groupName -> [ul, ...]
  const ungrouped = []; // extension reports catch-all

  navLists.forEach((ul) => {
    const linkTexts = Array.from(ul.querySelectorAll("a")).map((a) => a.textContent.trim());
    let matched = false;

    for (const group of SIDEBAR_GROUPS) {
      const hasMatch = linkTexts.some((text) =>
        group.patterns.some((pattern) => text.includes(pattern))
      );
      if (hasMatch) {
        if (!grouped.has(group.name)) grouped.set(group.name, []);
        grouped.get(group.name).push(ul);
        matched = true;
        break;
      }
    }

    if (!matched) {
      ungrouped.push(ul);
    }
  });

  // Build collapsible groups using plain <div> elements (avoids native <details> marker)
  const fragment = document.createDocumentFragment();

  function makeGroup(name, uls, open) {
    const group = document.createElement("div");
    group.className = "cqc-sidebar-group" + (open ? " open" : "");

    const title = document.createElement("div");
    title.className = "cqc-sidebar-group-title";
    title.textContent = name;
    title.addEventListener("click", () => group.classList.toggle("open"));
    group.appendChild(title);

    const body = document.createElement("div");
    body.className = "cqc-sidebar-group-body";
    uls.forEach((ul) => body.appendChild(ul));
    group.appendChild(body);

    return group;
  }

  for (const group of SIDEBAR_GROUPS) {
    const uls = grouped.get(group.name);
    if (!uls || uls.length === 0) continue;
    fragment.appendChild(makeGroup(group.name, uls, group.open));
  }

  // Extensions Québec catch-all
  if (ungrouped.length > 0) {
    fragment.appendChild(makeGroup("Extensions Québec", ungrouped, true));
  }

  // Replace original content: remove old <ul>s, append grouped fragment
  // Keep non-ul children (like inputs, forms) at the top
  const nonUlChildren = Array.from(aside.children).filter(
    (child) => !(child.tagName === "UL" && child.classList.contains("navigation"))
  );
  aside.innerHTML = "";
  nonUlChildren.forEach((child) => aside.appendChild(child));
  aside.appendChild(fragment);

  aside.dataset.cqcGrouped = "true";
}

const REPORT_INTROS = {
  income_statement: {
    titre: "État des résultats (revenus et dépenses)",
    explication:
      "Ce rapport montre tous les revenus gagnés et les dépenses engagées sur une période donnée. " +
      "Il permet de comprendre la rentabilité de votre entreprise : est-ce que vous gagnez plus que vous dépensez?",
    qui: "Vous, pour suivre la rentabilité. Votre CPA, pour préparer la déclaration T2/CO-17.",
    fonction: "Fava (comptes Revenus et Depenses dans Beancount)",
  },
  balance_sheet: {
    titre: "Bilan",
    explication:
      "Photo instantanée de ce que possède votre entreprise (actifs), ce qu'elle doit (passifs) " +
      "et sa valeur nette (capitaux propres) à une date précise. Actifs = Passifs + Capitaux propres.",
    qui: "Votre CPA, pour le bilan du T2. Vous, pour vérifier la santé financière de la société.",
    fonction: "Fava (comptes Actifs, Passifs, Capitaux-Propres dans Beancount)",
  },
  trial_balance: {
    titre: "Balance de vérification",
    explication:
      "Liste de tous les comptes avec leur solde débiteur ou créditeur. Si le total des débits " +
      "égale le total des crédits, vos livres sont équilibrés. C'est le document de base pour votre CPA.",
    qui: "Votre CPA, comme point de départ principal pour la déclaration fiscale.",
    fonction: "Fava (tous les comptes Beancount)",
  },
  journal: {
    titre: "Journal général",
    explication:
      "Registre chronologique de toutes les écritures comptables. Chaque transaction y apparaît " +
      "avec ses débits et crédits. Utile pour retracer comment une opération précise a été enregistrée.",
    qui: "Vous, pour vérifier une écriture. Votre CPA, pour valider les écritures.",
    fonction: "Fava (toutes les transactions Beancount)",
  },
  "extension/ApprobationExtension": {
    titre: "File d'approbation",
    explication:
      "Transactions catégorisées par l'intelligence artificielle qui attendent votre validation " +
      "avant d'être intégrées aux livres officiels. Approuver une transaction la déplace du fichier " +
      "temporaire (pending) vers le grand livre.",
    qui: "Vous, pour valider les suggestions de l'IA avant qu'elles ne deviennent officielles.",
    fonction: "compteqc.fava_ext.approbation (ApprobationExtension)",
  },
  "extension/PaieQCExtension": {
    titre: "Tableau de bord de la paie",
    explication:
      "Résumé cumulé de votre paie : salaire brut, toutes les retenues employé (RRQ/QPP, RQAP, " +
      "assurance-emploi, impôts fédéral et provincial) et les cotisations employeur (FSS, CNESST, " +
      "normes du travail). Le salaire net est ce qui est versé dans votre compte personnel.",
    qui: "Vous, pour suivre votre rémunération. Votre CPA, pour les feuillets T4/Relevé 1.",
    fonction: "compteqc.fava_ext.paie (PaieQCExtension)",
  },
  "extension/TaxesQCExtension": {
    titre: "Suivi TPS/TVQ",
    explication:
      "Suivi de la TPS (5%) et de la TVQ (9,975%) perçues sur vos factures et payées sur vos " +
      "achats. La différence entre les taxes perçues et les crédits de taxe sur intrants (CTI/RTI) " +
      "est le montant net à remettre au gouvernement.",
    qui: "Vous, pour préparer vos remises de taxes. Votre CPA, pour valider les montants.",
    fonction: "compteqc.fava_ext.taxes (TaxesQCExtension)",
  },
  "extension/DpaQCExtension": {
    titre: "Amortissement (DPA/CCA)",
    explication:
      "Suivi des immobilisations (ordinateurs, meubles, etc.) et de leur déduction pour " +
      "amortissement annuelle. Chaque catégorie a un taux prescrit par l'ARC (ex. : classe 50 " +
      "pour les ordinateurs à 55%).",
    qui: "Votre CPA, pour l'annexe DPA/CCA de la déclaration fiscale.",
    fonction: "compteqc.fava_ext.dpa (DpaQCExtension)",
  },
  "extension/PretActionnaireExtension": {
    titre: "Prêt actionnaire",
    explication:
      "Suivi des mouvements d'argent entre vous personnellement et votre société. Attention : " +
      "si la société vous prête de l'argent et qu'il n'est pas remboursé dans l'année suivant " +
      "la fin de l'exercice, ce montant devient un revenu imposable (article 15(2)).",
    qui: "Vous, pour éviter les pièges fiscaux. Votre CPA, pour vérifier la conformité.",
    fonction: "compteqc.fava_ext.pret_actionnaire (PretActionnaireExtension)",
  },
  "extension/ExportCPAExtension": {
    titre: "Export pour le comptable",
    explication:
      "Génère le dossier complet de fin d'année pour votre CPA : balance de vérification, " +
      "états financiers, annexes (paie, DPA, TPS/TVQ, prêt actionnaire) et codes IGRF/GIFI. " +
      "L'objectif : que votre CPA puisse tout réviser en moins d'une heure.",
    qui: "Votre CPA, comme dossier de travail principal.",
    fonction: "compteqc.fava_ext.export_cpa (ExportCPAExtension)",
  },
  "extension/EcheancesExtension": {
    titre: "Échéances fiscales",
    explication:
      "Calendrier des dates limites fiscales à venir : remise de TPS/TVQ, production des " +
      "feuillets T4/Relevé 1, déclarations T2/CO-17, acomptes provisionnels. Des alertes " +
      "de couleur indiquent l'urgence.",
    qui: "Vous, pour ne jamais manquer une échéance. Votre CPA, pour planifier son travail.",
    fonction: "compteqc.echeances.calendrier (EcheancesExtension)",
  },
  "extension/RecusExtension": {
    titre: "Reçus et factures",
    explication:
      "Téléchargez vos reçus et factures pour les associer aux transactions bancaires. " +
      "Cela crée une piste de vérification complète : chaque dépense est justifiée par " +
      "un document original en cas de contrôle fiscal.",
    qui: "Vous, pour conserver vos pièces justificatives. Votre CPA, pour la vérification.",
    fonction: "compteqc.documents.upload (RecusExtension)",
  },
};

/**
 * Pedagogical tooltip dictionary.
 * Keys match the exact textContent.trim() of table headers, KPI labels, and metric names.
 * Each value has `text` (French explanation) and optional `source` (Python function path).
 */
const TOOLTIPS = {
  // ===== Paie Québec (PaieQCExtension) =====
  "Salaire brut": {
    text: "Cumul annuel du salaire avant toute retenue. C'est le montant total que la société vous verse avant impôts et cotisations.",
    source: "paie.moteur.calculer_paie().salaire_brut",
  },
  "Salaire brut YTD": {
    text: "Cumul du salaire brut depuis le début de l'année (year-to-date). Sert à calculer si les maximums de cotisation sont atteints.",
    source: "paie.ytd.calculer_cumuls()",
  },
  "Retenues employé": {
    text: "Somme de toutes les déductions prélevées sur votre salaire : impôts fédéral et provincial, RRQ, RQAP et assurance-emploi.",
    source: "paie.moteur.calculer_paie()",
  },
  "Total retenues": {
    text: "Somme de toutes les déductions prélevées sur votre salaire : impôts fédéral et provincial, RRQ, RQAP et assurance-emploi.",
    source: "paie.moteur.calculer_paie()",
  },
  "Cotisations employeur": {
    text: "Montant additionnel payé par la société en plus de votre salaire : part employeur RRQ, RQAP, AE, FSS, CNESST et normes du travail.",
    source: "paie.moteur.calculer_paie()",
  },
  "Total employeur": {
    text: "Montant additionnel payé par la société en plus de votre salaire : part employeur RRQ, RQAP, AE, FSS, CNESST et normes du travail.",
    source: "paie.moteur.calculer_paie()",
  },
  "Salaire net": {
    text: "Montant déposé dans votre compte bancaire après toutes les retenues. Salaire brut moins toutes les déductions employé.",
    source: "paie.moteur.calculer_paie().salaire_net",
  },
  "Salaire net YTD": {
    text: "Montant déposé dans votre compte bancaire après toutes les retenues. Salaire brut moins toutes les déductions employé.",
    source: "paie.moteur.calculer_paie().salaire_net",
  },
  "RRQ (base)": {
    text: "Régime de rentes du Québec, cotisation de base. Cotisation retraite obligatoire prélevée sur le salaire entre l'exemption générale et le premier plafond.",
    source: "paie.cotisations.calculer_rrq_base()",
  },
  "RRQ (supp1)": {
    text: "Première cotisation supplémentaire RRQ (depuis 2024). Prélevée sur les mêmes gains que la cotisation de base, mais à un taux séparé.",
    source: "paie.cotisations.calculer_rrq_supp1()",
  },
  "RRQ (supp2)": {
    text: "Deuxième cotisation supplémentaire RRQ (depuis 2024). Prélevée sur les gains entre le premier et le deuxième plafond seulement.",
    source: "paie.cotisations.calculer_rrq_supp2()",
  },
  "RQAP": {
    text: "Régime québécois d'assurance parentale. Cotisation qui finance les congés de maternité, paternité et parentaux au Québec.",
    source: "paie.cotisations.calculer_rqap()",
  },
  "AE": {
    text: "Cotisation fédérale d'assurance-emploi. Le Québec a un taux réduit car le RQAP remplace la portion parentale de l'AE.",
    source: "paie.cotisations.calculer_ae()",
  },
  "Assurance-emploi": {
    text: "Cotisation fédérale d'assurance-emploi. Le Québec a un taux réduit car le RQAP remplace la portion parentale de l'AE.",
    source: "paie.cotisations.calculer_ae()",
  },
  "FSS": {
    text: "Fonds des services de santé. Taxe payée uniquement par l'employeur sur la masse salariale totale. Finance le système de santé du Québec.",
    source: "paie.cotisations.calculer_fss()",
  },
  "CNESST": {
    text: "Commission des normes, de l'équité, de la santé et de la sécurité du travail. Assurance obligatoire pour les accidents de travail.",
    source: "paie.cotisations.calculer_cnesst()",
  },
  "Normes du travail": {
    text: "Contribution obligatoire à la Commission des normes du travail. Finance l'application des lois du travail au Québec.",
    source: "paie.cotisations.calculer_normes_travail()",
  },
  "Impôt fédéral": {
    text: "Retenue d'impôt fédéral calculée selon les tables de retenues T4127, avec l'abattement du Québec de 16,5 % (les Québécois paient moins d'impôt fédéral car ils paient un impôt provincial séparé).",
    source: "paie.impots.calculer_impot_federal()",
  },
  "Impôt Québec": {
    text: "Retenue d'impôt provincial calculée selon le guide TP-1015.F-V de Revenu Québec.",
    source: "paie.impots.calculer_impot_quebec()",
  },
  "Impôt provincial": {
    text: "Retenue d'impôt provincial calculée selon le guide TP-1015.F-V de Revenu Québec.",
    source: "paie.impots.calculer_impot_quebec()",
  },
  "Coût total": {
    text: "Salaire brut + toutes les cotisations employeur. C'est le vrai coût d'un employé pour la société, bien plus que le salaire brut seul.",
    source: "paie.moteur.calculer_paie()",
  },
  "Maximum atteint": {
    text: "Ce symbole indique que la cotisation annuelle maximale est atteinte. Les prélèvements s'arrêtent automatiquement pour le reste de l'année.",
    source: null,
  },
  "Période": {
    text: "Le numéro de la paie dans l'année. Par exemple 12/26 signifie la 12e paie sur 26 périodes bi-hebdomadaires.",
    source: null,
  },

  // ===== TPS/TVQ (TaxesQCExtension) =====
  "TPS perçue": {
    text: "Taxe sur les produits et services (5 %) facturée à vos clients. Vous la collectez pour le gouvernement fédéral.",
    source: "taxes.sommaire.calculer_sommaire_tps_tvq()",
  },
  "TVQ perçue": {
    text: "Taxe de vente du Québec (9,975 %) facturée à vos clients. Vous la collectez pour Revenu Québec.",
    source: "taxes.sommaire.calculer_sommaire_tps_tvq()",
  },
  "TPS payée": {
    text: "Crédit de taxe sur les intrants (CTI). TPS payée sur vos achats d'affaires que vous pouvez récupérer du gouvernement fédéral.",
    source: "taxes.sommaire.calculer_sommaire_tps_tvq()",
  },
  "CTI": {
    text: "Crédit de taxe sur les intrants. TPS payée sur vos achats d'affaires que vous pouvez récupérer du gouvernement fédéral.",
    source: "taxes.sommaire.calculer_sommaire_tps_tvq()",
  },
  "TVQ payée": {
    text: "Remboursement de la taxe sur les intrants (RTI). TVQ payée sur vos achats d'affaires que vous pouvez récupérer de Revenu Québec.",
    source: "taxes.sommaire.calculer_sommaire_tps_tvq()",
  },
  "RTI": {
    text: "Remboursement de la taxe sur les intrants. TVQ payée sur vos achats d'affaires que vous pouvez récupérer de Revenu Québec.",
    source: "taxes.sommaire.calculer_sommaire_tps_tvq()",
  },
  "Net à remettre": {
    text: "Taxes perçues moins taxes payées = ce que vous devez envoyer au gouvernement. Si négatif, vous avez droit à un remboursement.",
    source: "taxes.sommaire.calculer_sommaire_tps_tvq()",
  },
  "Remise nette": {
    text: "Taxes perçues moins taxes payées = ce que vous devez envoyer au gouvernement. Si négatif, vous avez droit à un remboursement.",
    source: "taxes.sommaire.calculer_sommaire_tps_tvq()",
  },

  // ===== DPA/CCA (DpaQCExtension) =====
  "FNACC ouverture": {
    text: "Fraction non amortie du coût en capital au début de l'année. C'est la valeur comptable restante de vos actifs avant l'amortissement de cette année.",
    source: "dpa.calcul.calculer_dpa()",
  },
  "UCC ouverture": {
    text: "Undepreciated capital cost at year start (équivalent anglais de FNACC ouverture). Valeur comptable restante de vos actifs.",
    source: "dpa.calcul.calculer_dpa()",
  },
  "Acquisitions": {
    text: "Nouveaux actifs achetés pendant l'année, classés par catégorie (ordinateurs, meubles, véhicules, etc.).",
    source: "dpa.registre.RegistreActifs",
  },
  "Dispositions": {
    text: "Actifs vendus ou mis au rebut pendant l'année. Le produit de disposition réduit la FNACC de la catégorie.",
    source: "dpa.registre.RegistreActifs",
  },
  "DPA réclamée": {
    text: "Déduction pour amortissement que vous pouvez réclamer cette année. Réduit votre revenu imposable. La DPA est optionnelle et discrétionnaire.",
    source: "dpa.calcul.calculer_dpa()",
  },
  "DPA de l'année": {
    text: "Déduction pour amortissement que vous pouvez réclamer cette année. Réduit votre revenu imposable. La DPA est optionnelle et discrétionnaire.",
    source: "dpa.calcul.calculer_dpa()",
  },
  "CCA de l'année": {
    text: "Capital cost allowance (équivalent anglais de DPA). Déduction pour amortissement que vous pouvez réclamer cette année.",
    source: "dpa.calcul.calculer_dpa()",
  },
  "FNACC fermeture": {
    text: "Valeur comptable restante à la fin de l'année. Calcul : FNACC ouverture + acquisitions - dispositions - DPA.",
    source: "dpa.calcul.calculer_dpa()",
  },
  "UCC fermeture": {
    text: "Undepreciated capital cost at year end. Équivalent anglais de FNACC fermeture.",
    source: "dpa.calcul.calculer_dpa()",
  },
  "Taux": {
    text: "Le pourcentage de déduction annuel fixé par le gouvernement pour cette classe d'actifs. Chaque catégorie a son propre taux.",
    source: null,
  },
  "Classe 8": {
    text: "Mobilier, appareils et équipement de bureau. Taux d'amortissement : 20 % par année (dégressif).",
    source: null,
  },
  "Classe 10": {
    text: "Véhicules automobiles. Taux d'amortissement : 30 % par année (dégressif).",
    source: null,
  },
  "Classe 12": {
    text: "Logiciels et petit outillage (moins de 500 $). Taux d'amortissement : 100 % (déduction complète la première année).",
    source: null,
  },
  "Classe 50": {
    text: "Matériel informatique (ordinateurs, écrans, serveurs) acheté après 2023. Taux d'amortissement : 55 % par année (dégressif).",
    source: null,
  },
  "Classe 54": {
    text: "Véhicules zéro émission. Taux d'amortissement variable selon les incitatifs fiscaux en vigueur.",
    source: null,
  },
  "Règle du demi-taux": {
    text: "La première année d'acquisition, seulement 50 % de la DPA normale est permise. C'est la règle du demi-taux (half-year rule).",
    source: "dpa.calcul.calculer_dpa()",
  },
  "Half-year rule": {
    text: "La première année d'acquisition, seulement 50 % de la DPA normale est permise (règle du demi-taux).",
    source: "dpa.calcul.calculer_dpa()",
  },

  // ===== Prêt actionnaire (PretActionnaireExtension) =====
  "Solde net": {
    text: "Balance nette du compte de prêt actionnaire. Positif = la société vous doit de l'argent. Négatif = vous devez de l'argent à la société.",
    source: "pret_actionnaire.suivi.obtenir_etat_pret()",
  },
  "Direction": {
    text: "Indique qui doit de l'argent à qui : société vers actionnaire ou actionnaire vers société.",
    source: null,
  },
  "Avances ouvertes": {
    text: "Montants prêtés à l'actionnaire qui n'ont pas encore été remboursés. Chaque avance a sa propre date limite de remboursement.",
    source: null,
  },
  "Date limite s.15(2)": {
    text: "Si un prêt n'est pas remboursé avant cette date (1 an après la fin de l'exercice fiscal), le montant est ajouté à votre revenu personnel et imposé.",
    source: "pret_actionnaire.suivi.verifier_delais_s152()",
  },
  "Compte à rebours": {
    text: "Nombre de jours restants avant la date limite de l'article 15(2). Rouge = action immédiate requise.",
    source: null,
  },
  "Alerte critique": {
    text: "Moins de 30 jours avant l'inclusion au revenu selon l'article 15(2) de la Loi de l'impôt. Action immédiate requise pour éviter l'imposition.",
    source: null,
  },
  "Alerte urgente": {
    text: "Moins de 90 jours (3 mois) avant l'inclusion au revenu selon l'article 15(2). Planifiez le remboursement rapidement.",
    source: null,
  },

  // ===== File d'approbation (ApprobationExtension) =====
  "Confiance": {
    text: "Probabilité (0-100 %) que la catégorie suggérée par l'IA est correcte. Plus c'est haut, plus le système est sûr de son choix.",
    source: "categorisation.pipeline.PipelineCategorisation",
  },
  "Source IA": {
    text: "Quel moteur a catégorisé cette transaction : règle = système de règles automatiques, ml = apprentissage automatique, llm = Claude (intelligence artificielle).",
    source: "categorisation.pipeline",
  },
  "Compte proposé": {
    text: "Le compte comptable suggéré par l'IA pour cette transaction. Vous pouvez le modifier avant d'approuver.",
    source: null,
  },
  "Catégorie proposée": {
    text: "La catégorie comptable suggérée par l'IA pour cette transaction. Vous pouvez la modifier avant d'approuver.",
    source: null,
  },
  "Bénéficiaire": {
    text: "Le nom du fournisseur ou du destinataire du paiement tel qu'il apparaît sur le relevé bancaire.",
    source: null,
  },
  "Gros montant": {
    text: "Transactions de plus de 2 000 $ qui nécessitent une confirmation explicite avant approbation, par mesure de prudence.",
    source: null,
  },

  // ===== Native Fava tables =====
  "Account": {
    text: "Le nom du compte comptable dans le plan comptable. Chaque transaction touche au moins 2 comptes (débit et crédit).",
    source: null,
  },
  "Compte": {
    text: "Le nom du compte comptable dans le plan comptable. Chaque transaction touche au moins 2 comptes (débit et crédit).",
    source: null,
  },
  "Balance": {
    text: "Le solde du compte. Débit positif pour les actifs et dépenses, crédit positif pour les passifs, capitaux propres et revenus.",
    source: null,
  },
  "Position": {
    text: "La valeur totale détenue dans ce compte, incluant la devise. Représente le solde à la date sélectionnée.",
    source: null,
  },
  "Change": {
    text: "La variation du solde pendant la période sélectionnée. Montre combien le compte a augmenté ou diminué.",
    source: null,
  },
  "Narration": {
    text: "La description de la transaction telle qu'importée de la banque ou saisie manuellement.",
    source: null,
  },
  "Date": {
    text: "La date à laquelle la transaction a été enregistrée dans le grand livre (ledger).",
    source: null,
  },
};

/**
 * Attach pedagogical tooltips to table headers, KPI labels/values, and section titles.
 * Idempotent: removes all existing tooltips before re-attaching.
 */
function attachTooltips() {
  // 1. Idempotent cleanup: remove ALL existing data-tooltip and tabindex from previously tooltipped elements
  document.querySelectorAll("[data-tooltip]").forEach((el) => {
    el.removeAttribute("data-tooltip");
    el.removeAttribute("tabindex");
  });

  // 2. Query all potential tooltip targets
  const selectors = [
    ".cqc-table th",              // extension report table headers
    ".cqc-kpi-label",             // KPI tile labels
    ".cqc-kpi-value",             // KPI values (use parent label for lookup)
    "article table th",           // native Fava table headers
    ".cqc-section-title",         // section titles
  ];
  const elements = document.querySelectorAll(selectors.join(", "));

  elements.forEach((el) => {
    let lookupKey;

    // Special handling for .cqc-kpi-value: use sibling .cqc-kpi-label text
    if (el.classList.contains("cqc-kpi-value")) {
      const parent = el.closest(".cqc-kpi");
      if (parent) {
        const label = parent.querySelector(".cqc-kpi-label");
        if (label) {
          lookupKey = label.textContent.trim();
        }
      }
      if (!lookupKey) return;
    } else {
      lookupKey = el.textContent.trim();
    }

    // Exact match
    let tip = TOOLTIPS[lookupKey];

    // Fallback: case-insensitive match
    if (!tip) {
      const lowerKey = lookupKey.toLowerCase();
      for (const [key, value] of Object.entries(TOOLTIPS)) {
        if (key.toLowerCase() === lowerKey) {
          tip = value;
          break;
        }
      }
    }

    if (!tip) return;

    // Format tooltip text as single line (CSS attr() does not support newlines)
    const tooltipText = tip.source
      ? tip.text + " | Source : " + tip.source
      : tip.text;

    el.setAttribute("data-tooltip", tooltipText);
    el.setAttribute("tabindex", "0");
  });
}

function initTooltipPopup() {
  // Idempotent: only create once
  if (document.getElementById('cqc-tooltip-popup')) return;

  const popup = document.createElement('div');
  popup.id = 'cqc-tooltip-popup';
  document.body.appendChild(popup);

  // Single delegated listener on document
  document.addEventListener('mouseover', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (!target) {
      hideTooltip();
      return;
    }
    showTooltip(target);
  });

  document.addEventListener('mouseout', (e) => {
    // Only hide if leaving the tooltipped element entirely
    const target = e.target.closest('[data-tooltip]');
    if (target && !target.contains(e.relatedTarget)) {
      hideTooltip();
    }
  });

  // Keyboard: show on focus, hide on blur
  document.addEventListener('focusin', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (target) showTooltip(target);
  });

  document.addEventListener('focusout', (e) => {
    const target = e.target.closest('[data-tooltip]');
    if (target) hideTooltip();
  });
}

function showTooltip(el) {
  const popup = document.getElementById('cqc-tooltip-popup');
  if (!popup) return;

  const text = el.getAttribute('data-tooltip');
  if (!text) return;

  const rect = el.getBoundingClientRect();
  const margin = 8;
  const maxW = 320;
  const vw = window.innerWidth;

  popup.textContent = text;

  // Position: left-aligned to element, clamped so popup stays within viewport.
  // CSS transform: translateY(-100%) translateY(-8px) places it above the element.
  const left = Math.max(margin, Math.min(rect.left, vw - maxW - margin));
  const top = rect.top;

  popup.style.left = left + 'px';
  popup.style.top = top + 'px';
  popup.classList.add('cqc-tooltip-visible');
}

function hideTooltip() {
  const popup = document.getElementById('cqc-tooltip-popup');
  if (popup) {
    popup.classList.remove('cqc-tooltip-visible');
  }
}

function injectReportHeader() {
  const article = document.querySelector("article");
  if (!article) return;

  // Idempotent cleanup: remove existing intro
  const existing = article.querySelector(".cqc-report-intro");
  if (existing) existing.remove();

  const path = window.location.pathname;
  let matchedIntro = null;

  for (const [key, intro] of Object.entries(REPORT_INTROS)) {
    if (path.includes(key)) {
      matchedIntro = intro;
      break;
    }
  }

  if (!matchedIntro) return;

  const div = document.createElement("div");
  div.className = "cqc-report-intro cqc-card";
  div.innerHTML =
    "<h3>" + matchedIntro.titre + "</h3>" +
    "<p>" + matchedIntro.explication + "</p>" +
    "<p><strong>Qui utilise ce rapport :</strong> " + matchedIntro.qui + "</p>" +
    '<p class="cqc-source-tag">Source : ' + matchedIntro.fonction + "</p>";

  article.prepend(div);
}

// ===== Chart.js Infrastructure =====

/** @type {AbortController|null} Keyboard handler cleanup for SPA navigation */
let keyboardController = null;

/** @type {Promise<void>|null} */
let chartJsPromise = null;

/** @type {Map<string, object>} Chart.js instances keyed by container/canvas ID */
const chartRegistry = new Map();

/**
 * Lazy-load Chart.js 4.4.8 UMD from CDN.
 * Returns a cached Promise so the script is only injected once.
 * @returns {Promise<void>}
 */
function loadChartJs() {
  if (window.Chart) return Promise.resolve();
  if (chartJsPromise) return chartJsPromise;

  chartJsPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Chart.js from CDN'));
    document.head.appendChild(script);
  });

  return chartJsPromise;
}

/**
 * Destroy all tracked Chart.js instances and clear the registry.
 * Called at the top of every SPA navigation to prevent canvas reuse errors.
 */
function destroyAllCharts() {
  chartRegistry.forEach((chart) => {
    try { chart.destroy(); } catch (_) { /* already destroyed */ }
  });
  chartRegistry.clear();
}

/**
 * Return Quebec-palette default options for a given chart type.
 * @param {string} type - Chart type ('line', 'bar', 'doughnut', etc.)
 * @returns {object}
 */
function getChartThemeOptions(type) {
  const qcBlue = '#003DA5';
  const qcBlueAlpha = 'rgba(0,61,165,0.7)';
  const gridColor = 'rgba(0,61,165,0.08)';
  const frCACallback = (v) => v.toLocaleString('fr-CA') + ' $';

  switch (type) {
    case 'line':
      return {
        elements: {
          line: { tension: 0.3, borderColor: qcBlue, borderWidth: 2 },
          point: { radius: 0, hoverRadius: 6, backgroundColor: qcBlue },
        },
        scales: {
          y: { ticks: { callback: frCACallback }, grid: { color: gridColor } },
          x: { grid: { display: false } },
        },
      };
    case 'bar':
      return {
        elements: {
          bar: { backgroundColor: qcBlueAlpha, borderRadius: 4 },
        },
        scales: {
          y: { ticks: { callback: frCACallback }, grid: { color: gridColor } },
          x: { grid: { display: false } },
        },
      };
    case 'doughnut':
      return {
        plugins: {
          legend: {
            position: 'right',
            labels: { padding: 16, usePointStyle: true },
          },
        },
        backgroundColor: [
          qcBlue, '#1A5BBF', '#4A7FD4', '#7AA3E5', '#A6C4F0',
          '#16A34A', '#EA580C', '#D97706', '#DC2626', '#64748B',
        ],
      };
    default:
      return {};
  }
}

/**
 * Discover all [data-chart] containers in the page, load Chart.js on demand,
 * and create Chart instances with Quebec-themed defaults.
 * Fire-and-forget safe -- errors are logged, never thrown.
 */
async function renderCharts() {
  destroyAllCharts();

  const containers = document.querySelectorAll('.cqc-chart-container[data-chart]');
  if (containers.length === 0) return;

  await loadChartJs();

  containers.forEach((container, index) => {
    try {
      const canvas = container.querySelector('canvas');
      if (!canvas) return;

      const data = JSON.parse(container.dataset.chart);
      const type = container.dataset.chartType || 'bar';

      let customOptions = {};
      if (container.dataset.chartOptions) {
        try { customOptions = JSON.parse(container.dataset.chartOptions); } catch (_) { /* ignore bad JSON */ }
      }

      const chartInstance = new window.Chart(canvas, {
        type,
        data,
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: {
                font: { family: "'Inter', sans-serif" },
              },
            },
          },
          ...getChartThemeOptions(type),
          ...customOptions,
        },
      });

      chartRegistry.set(container.id || canvas.id || 'chart-' + index, chartInstance);
    } catch (err) {
      console.error('[CompteQC] Chart render error:', err);
    }
  });
}

// ===== Animation Infrastructure =====

/** @type {MediaQueryList|null} */
let reducedMotionQuery = null;

/**
 * Check if user prefers reduced motion (accessibility).
 * Caches the MediaQueryList for reuse.
 * @returns {boolean}
 */
function prefersReducedMotion() {
  if (!reducedMotionQuery) {
    reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  }
  return reducedMotionQuery.matches;
}

/**
 * Animate page entry: subtle fade + translateY on the article element.
 * Suppressed when prefers-reduced-motion is enabled.
 */
function animatePageEntry() {
  if (prefersReducedMotion()) return;

  const article = document.querySelector('article');
  if (!article) return;

  article.classList.remove('cqc-page-entering');
  void article.offsetWidth; // force reflow
  article.classList.add('cqc-page-entering');
}

/**
 * Animate KPI values from 0 to their target using requestAnimationFrame.
 * Discovers [data-value] elements, formats with Intl.NumberFormat fr-CA.
 * Suppressed when prefers-reduced-motion is enabled (leaves server-rendered text).
 */
function animateKPIs() {
  const elements = document.querySelectorAll('.cqc-kpi-value[data-value]');
  if (elements.length === 0) return;
  if (prefersReducedMotion()) return;

  elements.forEach((el) => {
    const target = parseFloat(el.dataset.value);
    if (isNaN(target)) return;

    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix !== undefined ? el.dataset.suffix : ' $';
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const duration = 800;
    const formatter = new Intl.NumberFormat('fr-CA', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });

    const startTime = performance.now();

    function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;

      if (progress >= 1) {
        // Final exact value to avoid floating point drift
        el.textContent = prefix + formatter.format(target) + suffix;
        return;
      }

      el.textContent = prefix + formatter.format(current) + suffix;
      requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  });
}

// ===== Approval Queue: Keyboard Shortcuts =====

/**
 * Initialize keyboard shortcuts for the Approbation approval queue.
 * j/k navigate rows, Space/Enter toggle checkbox, a clicks approve.
 * Uses AbortController for clean SPA navigation teardown.
 */
function initApprovalKeyboard() {
  // Clean up previous listener (SPA navigation cleanup)
  if (keyboardController) keyboardController.abort();
  keyboardController = new AbortController();

  // Only activate on Approbation page
  if (!window.location.pathname.includes("ApprobationExtension")) return;

  const rows = document.querySelectorAll(".cqc-table tbody tr[data-row-index]");
  if (rows.length === 0) return;

  let focusedRow = -1;

  function focusRow(index) {
    rows.forEach(r => r.classList.remove("cqc-row-focused"));
    if (index >= 0 && index < rows.length) {
      focusedRow = index;
      rows[index].classList.add("cqc-row-focused");
      rows[index].scrollIntoView({ block: "nearest" });
    }
  }

  document.addEventListener("keydown", (e) => {
    // Don't capture when typing in inputs
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;

    switch(e.key) {
      case "j":
        e.preventDefault();
        focusRow(Math.min(focusedRow + 1, rows.length - 1));
        break;
      case "k":
        e.preventDefault();
        focusRow(Math.max(focusedRow - 1, 0));
        break;
      case " ":
      case "Enter":
        if (focusedRow >= 0) {
          const cb = rows[focusedRow].querySelector('input[type="checkbox"]');
          if (cb) { cb.checked = !cb.checked; e.preventDefault(); }
        }
        break;
      case "a":
        // Click the approve/submit button
        const approveBtn = document.querySelector('.cqc-btn-success[type="submit"]') ||
                           document.querySelector('button[type="submit"].cqc-btn-success');
        if (approveBtn) { approveBtn.click(); }
        break;
    }
  }, { signal: keyboardController.signal });
}

// ===== Sidebar Badge: Pending Approval Count =====

/**
 * Fetch pending approval count and inject a red badge into the sidebar link.
 * Fire-and-forget -- errors are silently caught (badge is cosmetic).
 */
async function updateSidebarBadge() {
  try {
    // Find the Approbation link in sidebar
    const links = document.querySelectorAll("aside a, nav a");
    const link = Array.from(links).find(a =>
      a.textContent.includes("Approbation") || a.href.includes("ApprobationExtension")
    );
    if (!link) return;

    // Remove existing badge first (always clean up)
    const existing = link.querySelector(".cqc-sidebar-badge");
    if (existing) existing.remove();

    // Determine the base path (Fava uses /<bfile-slug>/extension/...)
    const pathParts = window.location.pathname.split("/");
    const bfileSlug = pathParts[1] || "";
    const resp = await fetch(`/${bfileSlug}/extension/ApprobationExtension/count`);
    if (!resp.ok) return;

    const data = await resp.json();
    if (data.count > 0) {
      const badge = document.createElement("span");
      badge.className = "cqc-sidebar-badge";
      badge.textContent = String(data.count);
      link.style.display = "inline-flex";
      link.style.alignItems = "center";
      link.appendChild(badge);
    }
  } catch (e) {
    // Silently fail -- badge is cosmetic, should never break the page
  }
}

/** @type import("fava").ExtensionModule */
export default {
  init() {
    injectStyle();
    loadChartJs(); // Non-blocking pre-load
  },
  onPageLoad() {
    animatePageEntry();
    injectStyle();
    initTooltipPopup();
    injectBrand();
    reorganizeSidebar();
    injectReportHeader();
    attachTooltips();
    renderCharts();
    animateKPIs();
    initApprovalKeyboard();
    updateSidebarBadge();
  },
};
