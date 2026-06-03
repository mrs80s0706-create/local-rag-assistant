# Project Kickoff Meeting — Minutes

**Date:** 2025-09-15  
**Attendees:** Alice Chen (PM), Bob Tanaka (Engineering Lead), Carol Davis (Design), David Lee (QA)  
**Facilitator:** Alice Chen

---

## 1. Project Overview

The team reviewed the scope of **Project Lighthouse**, an internal tool for automating monthly reporting. The goal is to reduce manual report generation time from approximately 8 hours per month to under 30 minutes.

Key deliverables agreed upon:
- A data ingestion pipeline that pulls from three internal data sources (CRM, billing system, support tickets)
- An automated report template engine
- A web-based preview and export interface

---

## 2. Timeline

| Milestone | Target Date | Owner |
|-----------|-------------|-------|
| Requirements finalised | 2025-09-30 | Alice |
| Backend API v1 | 2025-10-31 | Bob |
| UI prototype | 2025-10-25 | Carol |
| QA test plan | 2025-10-28 | David |
| Beta release | 2025-11-15 | All |
| Production launch | 2025-12-01 | All |

---

## 3. Technical Decisions

**Backend:** Python 3.11 + FastAPI. Bob proposed using async endpoints from the start given expected concurrent usage.

**Database:** PostgreSQL 15. The billing data will be stored in a separate schema to simplify access control.

**Frontend:** React 18 with TypeScript. Carol confirmed the design system already covers the required components.

**Authentication:** Existing company SSO (OAuth 2.0) will be used. No new credentials required for end-users.

---

## 4. Risks and Mitigations

1. **CRM API rate limits** — The CRM vendor imposes a 100 requests/minute cap. Bob will implement a local caching layer to avoid hitting this limit during report generation.

2. **Data privacy** — Reports may contain personally identifiable information. David will add a PII-redaction step to the QA checklist.

3. **Stakeholder availability** — Two key stakeholders are on leave in October. Alice will schedule review sessions in the first two weeks of October.

---

## 5. Action Items

- [ ] Alice: Send calendar invites for weekly syncs (by 2025-09-17)
- [ ] Bob: Share draft API schema in the team wiki (by 2025-09-22)
- [ ] Carol: Upload initial wireframes to Figma (by 2025-09-22)
- [ ] David: Draft QA strategy document (by 2025-09-29)

---

## 6. Next Meeting

**Date:** 2025-09-22, 10:00–11:00 (UTC+9)  
**Agenda:** API schema review + wireframe walkthrough
