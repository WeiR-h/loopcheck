# v0.4 interface checks

Observed on the local application on 2026-09-09:

- Chinese: sample connection, live proposal, expanded steps, confirmation, baseline and outcome.
- English: current project and latest MCP outcome, next-step text, requirements/history and stored goal after reload.
- Desktop 1280×900: source/version context and actionable result; no horizontal overflow (document width 1265, viewport 1280); console error log empty in the final inspection.
- The attempted 390×844 browser viewport override did not change the actual viewport. Mobile responsiveness is therefore **not verified in this run**; a desktop image is not labeled as a mobile check.
- Confirmed requirements keep their authored language when the UI language changes. They are not silently retranslated or rewritten.
- Keyboard focus and aria-live hooks exist in the implementation. This is not a complete accessibility compliance audit.

Screenshots under audit-v04 are actual viewport captures. The failed-result screenshot records the earlier arithmetic regression; the source has since been restored and rechecked.
