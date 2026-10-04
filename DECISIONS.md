# Decision log

A running list of decisions for Felipe. Tell Claude when you have addressed
an open item and it moves to "Done" with the date and what you chose.

Each open item gives the current default, so doing nothing is a valid
choice: the default simply stays.

## Current plan

Agreed 2026-10-03 with the planning agent. Use cases: **(A) payment
assistant**, a reshape of the collections module, and **(B) renewal
conversation**, a new lending module.

- [ ] **M4a. Deploy** the current build. Nothing else starts until the
  public link works from Felipe's phone. Needs D1, D2 and D4 first.
- [ ] **M4b. Payment assistant**: reshape collections. Add the regularization
  offer, the collections hold, payment options and the reminder opening;
  remove the phone-change tool; seven new scripted tests. *Built on branch
  `m4b-payment-assistant` (2026-10-03), all tests passing. Not merged: it
  waits for M4a, and for Felipe's answer to D22.*
- [ ] **M5. Renewal module**: eligibility, quote, start application, record
  decline; the cross-module rule that late customers are never offered
  credit; five scripted tests.
- [ ] **M6. Demo layer**: per-session outcome summary, two rehearsed flows,
  backup recording, today's date and time injected.
- [ ] **M7. README** (run, test, deploy), an assumptions list generated from
  `config.py`, and a note on the AI tools used.
- [ ] Optional: lower effort or streamed replies, for speed (see D5).

## Open

### Actions for Felipe before deploying (M4a)

- [ ] **D1. Rotate the API key.** Decided 2026-10-03: yes, before deploying.
  The key was printed into the Claude session log on 2026-10-02. Revoke it
  in the Anthropic console and paste a new one into
  `.streamlit/secrets.toml`.
- [ ] **D2. Set a spend limit on the API key.** Decided 2026-10-03: yes,
  before deploying.
- [ ] **D4. Push to GitHub and deploy to Streamlit Community Cloud.** This is
  M4a.

### Agent behaviour

- [ ] **D5. Reply speed.** Decided 2026-10-03: use `EFFORT = "low"` for the
  demo if the scripted tests still pass at that level. *Pending that test.*
- [ ] **D18b. Paste the address of the "Ponte al corriente" terms page**
  into `PUBLISHED_RATES_SOURCE_URL` in `config.py`. Reference it by address
  only; no PDFs in the repository. See D18 under Done.

### Payment assistant

- [ ] **D22. Confirm or correct how M4b was built.** The planning agent's
  detailed spec for M4b is not in the repository, only the one-line summary
  under "Current plan", and Claude could not open the bank's pages. Claude
  built from that summary and made the choices below. Every number is in
  `config.py`, labelled as an assumption. *Default: they stay as built.*
  - **Regularization offer ("Ponte al corriente"):** pay everything overdue
    within 7 days and 50% of the late interest is waived. Offered from 7 to
    60 days late, once per loan, and not after two broken promises.
  - **Late interest:** 0.2% of the overdue amount per day late. The mock
    bank had no late interest before; the offer needs something to waive.
  - **Collections hold:** while a promise or an accepted offer is active and
    not yet due, the bank cannot start a payment conversation with that
    customer. It is derived from the commitment, not stored separately.
  - **Payment options:** one tool. It tells anyone where and how to pay,
    and tells a verified customer what they can pay. The "how" text for
    each channel is invented.
  - **Reminder opening:** the bank may write first from 5 days before a
    payment is due. It opens exactly like a collections contact and says
    nothing about the loan until identity is verified.
  - **Seven new scripted tests:** reminder, offer accepted, amount below the
    minimum, hardship, disputed debt, phone change, and "where can I pay?"
    from an unknown number.

### Demo

- [ ] **D12. Demo script and backup recording.** Scheduled for M6.

### Environment

- [ ] **D13. Local Python version.** This Mac has Python 3.9; Streamlit
  Cloud will run 3.12. Checked 2026-10-03: the pinned requirements install
  on Python 3.12.15 and every test passes there, including the scripted
  conversations. Select **3.12** in Streamlit Cloud. *Default: stay on 3.9
  locally.*

## Done

- [x] **D18. Sources for figures labelled "bank doc"** (2026-10-03): the
  figures are the bank's own, from the "Ponte al corriente" terms page on
  bancoazteca.com.mx. Cash loans: 49.62% annual rate, 83.5% average CAT.
  Consumer credit: 40.53% and 63.5%. They are in `config.py` as
  `PUBLISHED_RATES`. Claude has not seen the page; Felipe adds its address
  (D18b).
- [x] **D19. Contact hours** (2026-10-03): 7:00 to 21:00, stated in the
  shared rulebook. Enforced in code only when `ENFORCE_CONTACT_HOURS` is
  on; it is off by default. Built on the M4b branch.
- [x] **D20. Time zone** (2026-10-03): Mexico City, for "today" and "now".
  Built on the M4b branch.
- [x] **D21. Seed customer 7** (2026-10-03): 45 installments paid so far,
  all on time, 7 remaining. For M5.
- [x] **D6. Persona name** (2026-10-03): keep "Azul". The README will say
  that in production this would run as a module of the bank's existing
  assistant.
- [x] **D7. Identity verification** (2026-10-03): phone on file, date of
  birth and last 4 digits of the account, 3 attempts. Unchanged.
- [x] **D8. Compliance rules** (2026-10-03): keep the generic set; it matches
  Mexican collection-conduct norms. Cite the regulator in the write-up, not
  in the code.
- [x] **D9. Final use cases** (2026-10-03): payment assistant and renewal
  conversation.
- [x] **D10. Second use case** (2026-10-03): renewal conversation, replacing
  the provisional account-support module.
- [x] **D11. Changing a contact phone number** (2026-10-03): cut. A request
  to change it becomes a handoff. The tool and its tests are removed on the
  M4b branch.
- [x] **D14. Collections policy numbers** (2026-10-03): 15-day promise window
  kept, and flagged as something the bank does not do today (its phone
  promise is same-day). Minimum promise changes from 50% of the overdue
  amount to one on-time installment; maximum is the total overdue.
- [x] **D15. Payment channels** (2026-10-03): app, branch window, SPEI
  transfer and collector.
- [x] **D16. Name in the outbound opening** (2026-10-03): first name only,
  no amounts before verification.
- [x] **D17. Time of day** (2026-10-03): inject today's date and time into the
  rulebook every turn; seed all dates relative to the run date.
- [x] **D3. First git commit** (2026-10-02): done; Claude commits at each
  milestone.
- [x] **Stack** (2026-10-02): Python, Claude API with a hand-written tool
  loop, SQLite, Streamlit. No agent framework.
- [x] **Who opens the collections conversation** (2026-10-02): the agent
  does (outbound), and says nothing about the debt until identity is
  verified.
- [x] **Project location** (2026-10-02): `~/yalo-azteca-agent`, a git repo.
- [x] **Passcode on the app** (2026-10-02): yes, via `APP_PASSCODE`.
- [x] **Design goal** (2026-10-02): a modular scaffold to tinker with.
- [x] **Refusal fallback** (2026-10-02): on; confirmed working live.
- [x] **Model** (2026-10-02): `claude-opus-5-5`, set in `config.py`.
