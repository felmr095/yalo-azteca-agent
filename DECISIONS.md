# Decision log

A running list of decisions for Felipe. Tell Claude when you have addressed
an open item and it moves to "Done" with the date and what you chose.

Each open item gives the current default, so doing nothing is a valid
choice: the default simply stays.

## Current plan

Agreed 2026-10-03 with the planning agent. Use cases: **(A) payment
assistant**, a reshape of the collections module, and **(B) renewal
conversation**, a new lending module.

- [x] **M4a. Deploy** the current build (2026-10-04): live at
  https://yalo-azteca-agent.streamlit.app, from `main`.
- [x] **M4b. Payment assistant** (2026-10-04): reshaped from collections,
  reconciled against the planner's spec, merged into `main` and pushed.
  66 policy tests and 16 scripted conversations passed before the merge.
  *Felipe tests the live link; if it is broken, Claude reverts the merge.*
- [x] **M5. Renewal module** (2026-10-04): eligibility, quote, start
  application, record decline; the cross-module rule that late customers
  are never offered credit. Merged into `main` and pushed. 93 policy tests
  and all 22 scripted conversations passed before the merge.
- [ ] **M6. Demo layer**: per-session outcome summary, two rehearsed flows,
  backup recording, today's date and time injected. *Done on branch
  `m6-demo-layer` (2026-10-04): the outcome summary in the sidebar, and the
  two flows written out in the README (Miguel Ángel, hardship; Carmen
  Beatriz, renewal quote). Still to do: the backup recording, and the time
  of day in the rulebook (D17).*
- [ ] **M7. README** (run, test, deploy), an assumptions list generated from
  `config.py`, and a note on the AI tools used. *Done on branch
  `m6-demo-layer` (2026-10-04): the README, rewritten for a reviewer who
  has not seen the project, and `python -m tools.transcript` to read a
  conversation log. Still to do: the assumptions list and the note on AI
  tools.*
- [ ] Optional: lower effort or streamed replies, for speed (see D5).

## Open

### Actions for Felipe

- [ ] **D1. Rotate the API key.** Decided 2026-10-03: yes, before deploying.
  The key was printed into the Claude session log on 2026-10-02. Revoke it
  in the Anthropic console and paste a new one into
  `.streamlit/secrets.toml`.
- [ ] **D2. Set a spend limit on the API key.** Decided 2026-10-03: yes,
  before deploying.
- [ ] **D24. Set GitHub's default branch to `main`.** It is
  `m4b-payment-assistant`, because the first push went out while that
  branch was checked out. Claude could not change it (the `gh` tool is not
  installed). Change it at
  https://github.com/felmr095/yalo-azteca-agent/settings, under General >
  Default branch.

### Agent behaviour

- [ ] **D5. Reply speed.** Decided 2026-10-03: use `EFFORT = "low"` for the
  demo if the scripted tests still pass at that level. *Pending that test.*
- [ ] **D18b. Paste the address of the "Ponte al corriente" terms page**
  into `PUBLISHED_RATES_SOURCE_URL` in `config.py`. Reference it by address
  only; no PDFs in the repository. See D18 under Done.

### Demo

- [ ] **D12. Demo script and backup recording.** Scheduled for M6.

### Environment

- [ ] **D13. Local Python version.** This Mac has Python 3.9; Streamlit
  Cloud will run 3.12. Checked 2026-10-03: the pinned requirements install
  on Python 3.12.15 and every test passes there, including the scripted
  conversations. Select **3.12** in Streamlit Cloud. *Default: stay on 3.9
  locally.*

## Done

- [x] **D29. Offers computed are stored** (2026-10-04): every catch-up offer
  worked out for a customer is kept in its own table
  (`regularization_offers`), accepted or not, so the outcome summary can
  show it. The customer is committed to nothing until a promise is
  registered.
- [x] **D30. Blocked contacts are part of the demo** (2026-10-04): picking a
  customer selects the start their story calls for. For Ana Karen, Ricardo
  Daniel and Sofía Alejandra that start is refused (collections hold, or
  the 30-day wait after a decline); the chat area and the Outcome section
  say why in one plain line.
- [x] **D27. Credit on the Anthropic account** (2026-10-04): the API refused
  every call for a while ("credit balance is too low"). Felipe added
  credit; calls work again.
- [x] **D28. Choices the renewal spec leaves open** (2026-10-04): all
  accepted, each labelled an assumption.
  - **Quote formula:** equal weekly payments at the published annual rate
    divided by 52, without IVA. An estimate, and said to the customer as
    one.
  - **Disclosure:** before asking the customer to go ahead, the agent states
    the weekly payment, the total to pay and the CAT (83.5%, a placeholder
    from the bank's published figures).
  - **Who has an offer:** only customers with a pre-approved limit on
    record.
  - **"Promise activity in 6 months":** any payment promise created in the
    last 180 days, kept or not.
  - **The 30-day wait** stops the bank from offering again. A customer who
    declined may still ask for a loan themselves.
  - **Opening:** the same as for payments (D23).
- [x] **Live tests** (2026-10-04): to save credit, after a change run only
  the scripted conversations it affects (`--only`), not the whole set.
- [x] **D23. What the outbound opening says before verification**
  (2026-10-04): kept as built. Before verification the opening names the
  bank and gives the reason only as "un asunto de su cuenta"; the loan is
  named only after. This is a deliberate trade-off. A specific opening
  leaks the debt to whoever holds the phone; a vague one looks like
  phishing. We accept the second risk and reduce it by never asking for
  anything but the two verification facts.
- [x] **D25. Numbers the spec leaves open** (2026-10-04): accepted, each
  labelled an assumption in `config.py`. On-time discount: 10% off the
  standard weekly payment. Pay-by date of the program: 7 days from today.
  A customer who is not late yet may promise a date after the due date,
  for one weekly payment, between the on-time and the standard price.
- [x] **D26. "Amount owed" in the catch-up offer** (2026-10-04): everything
  due by the pay-by date without the program: the missed payments and the
  coming one at the standard price, plus accrued late interest. The amount
  to pay is the same payments at the on-time price, and the amount waived
  is the difference, so the customer always pays less than they owe.
- [x] **D22. How M4b was built** (2026-10-04): replaced by the planner's
  spec. The invented offer (50% of late interest, 7 to 60 days late) and
  the invented daily late-interest rate are gone. "Ponte al corriente" now
  follows the bank's program as the spec gives it: 2 to 22 missed payments,
  not for a loan on a plan, once per loan; late interest and lost on-time
  discounts waived; the customer pays the missed payments at the on-time
  price plus the coming one. Kept from the first build: the collections
  hold, the phone-change handoff, where-to-pay without verification, and
  the core changes. The invented "how to pay" text per channel was dropped;
  the four channels and the cashier instruction remain.
- [x] **D4. Push to GitHub and deploy** (2026-10-04): done by Felipe.
  Secrets are set in the Streamlit dashboard.
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
- [x] **D17. Time of day** (2026-10-03, built 2026-10-04): the rulebook is
  given today's date and the time in Mexico City on every turn, with the
  greeting that goes with it; all seed dates are relative to the run date.
  Log and ticket timestamps are in Mexico City time too. Before this, on
  the live server (which runs on UTC) the agent said "buen día" at 17:17.
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
