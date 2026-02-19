---
status: diagnosed
trigger: "Jinja2 TemplateNotFound in EcheancesExtension - {% from 'compteqc.fava_ext.echeances' import couleur_urgence %}"
created: 2026-02-19T00:00:00
updated: 2026-02-19T00:00:00
---

## Current Focus

hypothesis: CONFIRMED - The template uses Jinja2 import syntax to load a Python function, which is fundamentally wrong. Jinja2 `{% from %}` resolves template files, not Python modules.
test: Read all involved files and compare against the working PretActionnaire pattern.
expecting: Confirmed root cause with a clear, safe fix path.
next_action: DONE - diagnosis complete, no code changes made.

## Symptoms

expected: EcheancesExtension renders its Fava report page correctly.
actual: Fava raises `jinja2.exceptions.TemplateNotFound: compteqc.fava_ext.echeances` when trying to render the template.
errors: `jinja2.exceptions.TemplateNotFound: compteqc.fava_ext.echeances`
reproduction: Load the Fava UI and navigate to the Echeances report page.
started: Since the EcheancesExtension template was written (likely introduced when the template was authored).

## Eliminated

- hypothesis: The Jinja2 template environment is misconfigured and cannot find templates at all.
  evidence: The PretActionnaire extension uses the same Fava extension mechanism and renders correctly with no import statements. The problem is specific to the `{% from %}` call on line 5.
  timestamp: 2026-02-19

- hypothesis: The function `couleur_urgence` is actually called correctly somewhere else and is working.
  evidence: Line 86 of the template uses `extension.module.couleur_urgence(...)` as a fallback, but the `{% from %}` on line 5 still runs first at template parse time and raises the error before the page body is ever rendered.
  timestamp: 2026-02-19

## Evidence

- timestamp: 2026-02-19
  checked: src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html line 5
  found: `{% from "compteqc.fava_ext.echeances" import couleur_urgence %}` - Jinja2 `{% from %}` expects a **template file path** relative to the template loader's search paths, not a Python module dotted path.
  implication: Jinja2 will attempt to open a file literally named `compteqc.fava_ext.echeances` (or `compteqc/fava_ext/echeances.html` depending on the loader) from the template search path. No such file exists. This is a category error: Python module paths and Jinja2 template paths are entirely different namespaces.

- timestamp: 2026-02-19
  checked: src/compteqc/fava_ext/echeances/__init__.py lines 20-35
  found: `couleur_urgence` is a plain Python function defined at module level. It takes an `urgence: str` argument and returns a CSS class name string from a dict lookup. It is NOT defined in any Jinja2 template file.
  implication: The only way to make this function available inside a Jinja2 template is to either (a) pass it as a context variable when rendering, or (b) expose it as a method on the extension object that the template can call via `extension.couleur_urgence(...)`.

- timestamp: 2026-02-19
  checked: src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html line 86
  found: The template body already contains a second, inconsistent attempt to call the function: `extension.module.couleur_urgence(alerte.urgence) if extension.module else 'alerte-info'`. This is also wrong because FavaExtensionBase has no `.module` attribute - this would produce an AttributeError at runtime even if line 5 were fixed.
  implication: Both the `{% from %}` on line 5 and the `extension.module.` call on line 86 need to be corrected. The real target is `extension.couleur_urgence(alerte.urgence)` since the method is defined on the extension class.

- timestamp: 2026-02-19
  checked: src/compteqc/fava_ext/pret_actionnaire/templates/PretActionnaireExtension.html (entire file)
  found: The PretActionnaire template contains NO `{% from %}` or `{% import %}` directives. It never calls `niveau_alerte_s152` directly by name. Instead, the Python method `s152_status()` (in `__init__.py` lines 98-154) calls `niveau_alerte_s152` internally and embeds the result string (`"normal"`, `"urgent"`, etc.) into the dict it returns. The template simply reads `s152.niveau_alerte` as a plain string value and uses it with `alerte-{{ s152.niveau_alerte }}` for CSS class interpolation.
  implication: This is the correct Fava extension pattern. Python helper functions are called **inside the Python method**, which returns a plain data dict. Templates consume plain data. Templates never import or call Python functions directly.

- timestamp: 2026-02-19
  checked: src/compteqc/fava_ext/pret_actionnaire/__init__.py lines 19-35 vs lines 98-154
  found: `niveau_alerte_s152` is a module-level Python helper. It is called on line 131 (`"niveau": niveau_alerte_s152(jours)`) and line 139 (`niveau = niveau_alerte_s152(jours_restants_min)`) from within `s152_status()`. The returned dict contains computed strings that the template reads. The template never sees or calls `niveau_alerte_s152` at all.
  implication: Exactly the same approach should be used for `couleur_urgence` in EcheancesExtension.

## Resolution

root_cause: |
  The Jinja2 template `EcheancesExtension.html` line 5 uses `{% from "compteqc.fava_ext.echeances" import couleur_urgence %}`, treating a Python module dotted path as if it were a Jinja2 template file path. Jinja2 `{% from %}` resolves template files from the template loader's search paths, not Python modules. Since no template file named `compteqc.fava_ext.echeances` exists on disk, Jinja2 raises `TemplateNotFound` immediately at template parse time, before any page content is rendered.

  A secondary defect exists on line 86: even if line 5 were somehow resolved, the expression `extension.module.couleur_urgence(...)` would raise `AttributeError` because `FavaExtensionBase` instances have no `.module` attribute. This is a second incorrect attempt to call the Python function from template context.

fix: |
  Apply the same pattern used successfully in PretActionnaireExtension:

  1. Remove the `{% from "compteqc.fava_ext.echeances" import couleur_urgence %}` line (line 5) from the template entirely.

  2. In `EcheancesExtension.__init__.py`, modify the `alertes()` method (or add a new method) to pre-compute and embed the CSS class string into each alert dict before returning it. For example:

     ```python
     def alertes(self) -> list[dict]:
         """Retourne la liste des alertes actives avec classe CSS pre-calculee."""
         result = []
         for alerte in self._alertes:
             result.append({
                 **alerte,
                 "classe_css": couleur_urgence(alerte["urgence"]),
             })
         return result
     ```

  3. In the template, replace the broken `extension.module.couleur_urgence(alerte.urgence)` expression on line 86 with `alerte.classe_css` (a plain string already in the dict):

     ```html
     <div class="alerte-banniere {{ alerte.classe_css }}">
     ```

  This keeps all Python logic in Python and gives the template only plain data to render — exactly the pattern PretActionnaireExtension uses for `niveau_alerte_s152`.

  Alternative (simpler, if alert dicts from the Phase 5 module cannot be modified): add `couleur_urgence` as a method on the `EcheancesExtension` class and call it from the template as `extension.couleur_urgence(alerte.urgence)`. Fava exposes the extension object to templates via the `extension` variable, so any public method is callable this way.

verification: Not applicable - diagnosis only, no code changes made per task instructions.
files_changed: []
