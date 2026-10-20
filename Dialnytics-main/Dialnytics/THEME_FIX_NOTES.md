# Dialnytics global theme patch

This package builds on Dialnytics_Consolidated_Code_Testing_Deferred.zip.

Changes:
- Centralized dark/light color tokens and theme-wide overrides.
- Unified dashboard charts, panels, logs, contact lists, voicemail, campaigns, users, tables, forms, script editor, navigation, profile dropdown and dialer rail.
- Corrected dark-on-dark and light-on-light contrast in headings and stats.
- Preserved moon (light) / sun (dark) toggle and saved browser preference.
- Applied saved theme earlier to reduce theme flash during loading.
- Removed compiled Python bytecode from ZIP.

Not performed: browser screenshot regression tests, live Telnyx calls or production deployment. Existing backend limitations remain unchanged.
