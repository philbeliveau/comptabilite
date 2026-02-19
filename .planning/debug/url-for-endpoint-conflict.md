---
status: diagnosed
trigger: "url_for() endpoint conflict in Fava templates - TypeError: url_for() got multiple values for argument 'endpoint'"
created: 2026-02-19T00:00:00Z
updated: 2026-02-19T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Flask url_for() receives 'endpoint' as both the first positional arg ('extension_endpoint') and as an explicit kwarg ('approuver'/'upload'/'rejeter'), causing a "multiple values for argument" TypeError.
test: Read Fava application.py route definition and cross-referenced with template calls.
expecting: N/A - root cause confirmed.
next_action: Fix is to rename the kwarg from `endpoint=` to whatever parameter name is safe. The Fava route uses `endpoint` as the URL path variable name, so the kwarg name IS correct for building the URL — the bug is that Flask reserves `endpoint` as its own positional argument name.

## Symptoms

expected: Templates render and URL is built correctly, e.g. `/mybfile/extension/ApprobationExtension/approuver`
actual: `TypeError: url_for() got multiple values for argument 'endpoint'`
errors: |
  TypeError: url_for() got multiple values for argument 'endpoint'
  File "ApprobationExtension.html", line 78
  File "RecusExtension.html", line 77
  File "ApprobationExtension.html", line 130
reproduction: Navigate to any Fava page that renders ApprobationExtension or RecusExtension templates.
started: Introduced when these templates were first written.

## Eliminated

(none - root cause confirmed on first hypothesis)

## Evidence

- timestamp: 2026-02-19T00:00:00Z
  checked: /Users/philippebeliveau/Desktop/Notebook/comptabilite/.venv/lib/python3.12/site-packages/fava/application.py lines 349-364
  found: |
    The route is defined as:
      @fava_app.route(
          "/<bfile>/extension/<extension_name>/<endpoint>",
          methods=["GET", "POST", "PUT", "DELETE"],
      )
      def extension_endpoint(extension_name: str, endpoint: str) -> Response:

    So the Fava route DOES use `endpoint` as the URL path variable name (the third segment after /extension/<extension_name>/).
  implication: |
    The Fava route genuinely expects a URL variable named `endpoint`. However, Flask's
    `url_for()` function signature is `url_for(endpoint_name, **values)` where the FIRST
    positional argument is the Flask endpoint name (i.e., the route function name or alias).
    Flask internally handles the first argument as `endpoint` in its own function signature.
    Passing `endpoint='approuver'` as a keyword argument therefore collides with Flask's
    own `endpoint` parameter, producing the "multiple values for argument 'endpoint'" error.

- timestamp: 2026-02-19T00:00:00Z
  checked: Template call sites (3 occurrences)
  found: |
    ApprobationExtension.html line 78:
      url_for('extension_endpoint', bfile=g.beancount_file_slug, extension_name=extension.name, endpoint='approuver')

    ApprobationExtension.html line 130:
      url_for('extension_endpoint', bfile=g.beancount_file_slug, extension_name=extension.name, endpoint='rejeter')

    RecusExtension.html line 77:
      url_for('extension_endpoint', bfile=g.beancount_file_slug, extension_name=extension.name, endpoint='upload')
  implication: All three call sites use the same incorrect pattern.

## Resolution

root_cause: |
  Flask's `url_for()` function treats its first positional argument as the internal
  `endpoint` parameter (the route function name). The Fava route for extension sub-pages
  happens to use `endpoint` as the name of its URL path variable:

      /<bfile>/extension/<extension_name>/<endpoint>

  This is a naming collision: Flask's own `endpoint` keyword and Fava's URL path variable
  `endpoint` share the same name. When the template calls:

      url_for('extension_endpoint', ..., endpoint='approuver')

  Flask sees `endpoint` passed TWICE — once as the positional route-function-name
  ('extension_endpoint') and once as an explicit kwarg ('approuver') — and raises:

      TypeError: url_for() got multiple values for argument 'endpoint'

  The Fava framework authors named the path variable `endpoint` in the route, and
  Flask's url_for() reserves that keyword for itself. There is no way to pass a URL
  path variable named `endpoint` via url_for() using a plain keyword argument.

fix: |
  NOT APPLIED (diagnose-only mode).

  The fix requires one of two approaches:

  APPROACH A — Use url_for with _anchor trick (not applicable here).

  APPROACH B — Build the URL manually instead of using url_for():
    Replace:
      url_for('extension_endpoint', bfile=g.beancount_file_slug, extension_name=extension.name, endpoint='approuver')
    With a manual string:
      "/" + g.beancount_file_slug + "/extension/" + extension.name + "/approuver"

  APPROACH C — Use Jinja2's `url_for` with **kwargs trick via a dict variable:
    This does NOT work in standard Flask/Jinja2 because url_for() does not accept
    **dict unpacking in templates.

  RECOMMENDED FIX (Approach B): Build the URL path as a string directly in the template.
  The pattern is consistent and Fava's URL structure is stable:

    ApprobationExtension.html line 78:
      action="/{{ g.beancount_file_slug }}/extension/{{ extension.name }}/approuver"

    ApprobationExtension.html line 130:
      action="/{{ g.beancount_file_slug }}/extension/{{ extension.name }}/rejeter"

    RecusExtension.html line 77:
      action="/{{ g.beancount_file_slug }}/extension/{{ extension.name }}/upload"

  This bypasses url_for() entirely and constructs the correct URL directly, which is
  safe because the Fava extension URL pattern is fixed and documented.

verification: NOT APPLIED (diagnose-only mode).

files_changed: []
