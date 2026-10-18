# Dialnytics update notes

## Updated
- Global light-mode surface/contrast overrides for dashboard panels, logs, contacts, forms and scripts.
- One session per user **per Python process**. A second login invalidates the previous browser session on its next authenticated request.

## Not implemented / production blockers
- True cross-instance single-device login requires shared durable session storage (e.g. PostgreSQL/Redis). This in-memory change does not enforce across workers or restarts.
- Terminating an active Telnyx call when another device logs in is not implemented.
- Incoming group ringing and decline-for-everyone require a verified Telnyx inbound routing/call-control design, durable coordination, signed webhook verification and live tests. Existing frontend incoming popup alone is not sufficient.
- Render Free ephemeral storage means user records, scripts, payment records and recordings are not durable. Do not onboard paying customers until persistent storage and webhook security are configured.

## Deployment
Keep existing environment variables; replace project files, commit, then manual deploy. Test light/dark across all pages. Do not upload `.env`, `users.json` or credentials.
