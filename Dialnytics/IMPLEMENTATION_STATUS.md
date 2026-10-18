# Dialnytics integration status

This is an implementation checkpoint, **not** a finished production calling system.

Implemented in this package:
- PostgreSQL-backed users and sessions from previous integration.
- Verified Telnyx webhook handling from previous integration.
- Database-atomic first-answer claim and group decline state transitions.
- Participant-authorized group status endpoint.
- Admin session revocation API.

**Not implemented / not safe to promise:**
- Telnyx Voice API fan-out dialing of actual WebRTC agents.
- Telnyx carrier hangup for decline-all and bridging the winning agent leg.
- Mapping SIP telephony credentials to Voice API dial destinations.
- Real-time browser integration of group endpoints and active-call termination.
- Persistent call logs, contacts, and recordings storage.
- Live integration testing or production readiness.

Do not move numbers from the existing SIP connection or deploy to live users yet.
