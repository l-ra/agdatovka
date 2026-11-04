# AGDA-28 — accessible management UI evidence

This is a dependency-free, static UI vertical slice for the `ag-synthetic`
offline fixture. It is not production UX evidence and does not claim external
delivery, accessibility conformance certification, or a public release.

## Source and reproduction

- Source: [`ui/index.html`](../../ui/index.html), [`ui/app.js`](../../ui/app.js), and [`ui/styles.css`](../../ui/styles.css)
- Fixture: [`fixtures/ui/management-scenario.json`](../../fixtures/ui/management-scenario.json)
- Automated checks: [`tests/test_ui_accessibility.py`](../../tests/test_ui_accessibility.py)
- Start API: `python3 -m ag_datovka.server --host 127.0.0.1 --port 8080`
- Serve UI: `python3 -m http.server 8000 --directory ui`
- Open `http://127.0.0.1:8000/`; use `http://127.0.0.1:8080/api/v1` and `dev:platform`.

The UI uses only `/api/v1`, adds an idempotency key to mutations, displays
problem details without raw response injection, and explicitly labels all
results as synthetic. Attachment bytes are generated from the text fixture;
the API remains authoritative for digest and length.

## Automated accessibility evidence

`python3 -m unittest tests.test_ui_accessibility -v` checks unique control IDs,
explicit labels, semantic status/error regions, focus recovery, keyboard
focus styling, required API action wiring, synthetic fixture scope, and the
absence of `innerHTML`/`document.write` injection paths. This is a source-level
check, not a replacement for assistive-technology testing.

## Manual scenario record

1. Tab from the address bar through connection, databox, access, message, and
   record controls; every control has a visible label and a visible yellow
   focus indicator.
2. Submit the message form before selecting a box; focus moves to the red
   error summary and the result is a redacted stable problem shape.
3. Connect, create a synthetic box, create an identity, assign a role, submit
   a text attachment, refresh the operation/lifecycle view, create an export,
   and refresh audit records.
4. Confirm the result panel is keyboard-focusable and the status/error text is
   announced through live regions.

Reviewer findings belong on the reviewer’s Paperclip task; this record only
documents the implementation and repeatable scenario.
