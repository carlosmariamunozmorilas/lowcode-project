# Data protection — the GDPR write-up

Brief requirement 6: *lawful basis, data minimisation, retention period, and who
can see personal data.* Written for the application as it would run in a real
team. In this project every record is invented — no real store, staff,
customers or figures — so no real personal data is processed during the course.

## What personal data there is

**Real-person data in the intended workflow is staff data.** The v2 demo's
shop orders and pseudonymous customer codes are entirely **synthetic**.

| Data | About whom | Why it is needed |
|---|---|---|
| Full name | Each team member | Shows who raised, owns, reviewed and certified each action — the point of the record |
| Work email | Each team member | Sign-in; where approval requests and reminders are sent |
| Password hash | Each team member who signs in | Sign-in. The password itself is never stored |
| Actor on each history row | Each team member | Who changed what, and when — the audit trail |

The KPIs are store-level aggregates: sessions, conversion rate, average order
value and spend. The v2 design also stores **fictional orders** with synthetic
pseudonymous customer codes for holdout tests; it does not receive real
customer names, emails, addresses or browsing data. If a real store were
connected later, pseudonymous order/customer identifiers could still be
**personal data** under GDPR, not anonymous by default. A live connection
would need a new data-flow, lawful-basis, retention and processor assessment.
See [Irish DPC: anonymisation and pseudonymisation](https://www.dataprotection.ie/en/dpc-guidance/anonymisation-pseudonymisation).

**One residual risk:** action titles, hypotheses and notes are free text, so a
person could type a customer's name into one. The form says not to, and the
automations never forward free text (see [`stride.md`](stride.md), T12 and T17).

## Lawful basis

**Proposed basis: legitimate interests** (Article 6(1)(f)) for agency work
allocation and audit records, **subject to** a documented necessity and
balancing assessment in Week 11; it is not automatically established just
because records concern work. Staff need an appropriate privacy notice and
retain applicable rights. Consent is generally unsuitable for mandatory
workplace processing. See [Irish DPC: legal bases](https://www.dataprotection.ie/en/dpc-guidance/guidance-legal-bases-processing-personal-data).

## Data minimisation

- Name, work email and role — nothing else about a person: no phone, no photo,
  no personal address, no tracking.
- Synthetic customer codes and fictional order rows only in the MVP; no real
  customer records. Reassess before any live store connection.
- Outward messages carry the action number and a link, never content
  ([`stride.md`](stride.md), T12).
- The AI provider receives aggregates only — no names
  ([`stride.md`](stride.md), T17).

## Retention

| Data | Kept for | Then |
|---|---|---|
| Actions, history, targets, measurements | The project period plus 24 months ❓ | Archived; the record is the business's accounting trail |
| A user who leaves | Account deactivated on the day | Pseudonymised after 12 months ❓ — see below |
| Outbound events | 90 days after delivery ❓ | Deleted — they are a delivery queue, not the record |
| Automation event payloads | 90 days ❓ | Deleted; the `(source, external_id)` key is kept so an old redelivery still changes nothing |

❓ The periods are proposals, to be confirmed in the Week 11 governance
document.

## Erasure without breaking the audit trail

The history tables cannot be edited — that is their purpose. So a request to
erase a former colleague does not delete their rows; it **pseudonymises the
user**: name becomes *Former user #17*, email becomes an address that cannot
receive mail, the account is deactivated. Every history row still points at
user 17, so the record stays intact and honest — *someone* approved this — but
no longer names the person. This is decided now because it is the one place
where the project's main invariant, a record that cannot be rewritten, meets a
data-protection right.

## Who can see personal data

| Who | Sees |
|---|---|
| Every signed-in team member | Names on actions and their history — needed to know who is waiting on whom |
| Admin | Names, emails and roles; user administration |
| The named reviewer | Their own approval requests by email or Slack |
| Make (processor) | The named reviewer's email, to send approval requests; names never sent onward to the AI provider |
| Email / Slack provider (processor) | The messages it delivers |
| AI provider (processor) | Aggregates only by design; still assess whether free-text or identifiers could leak into prompts |

Make, the mail provider and the AI provider are **processors** and would need a
data-processing agreement with a real client. Where each stores data — Make
offers an EU region — is recorded when each automation is written up.
