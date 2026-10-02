# Decision log

A running list of decisions for Felipe. Open items wait for your call; none
of them block the build unless marked **blocking**. Tell Claude when you
have addressed one and it moves to "Done" with the date and what you chose.

Each open item gives the current default, so doing nothing is a valid
choice: the default simply stays.

## Open

### Security and cost

- [ ] **D1. Rotate the API key.** The key was printed into the Claude
  session log on 2026-10-02. Revoke it in the Anthropic console and paste a
  new one into `.streamlit/secrets.toml`. *Default: old key stays in use.*
- [ ] **D2. Set a spend limit on the API key.** Needed before the app is on
  a public link. *Default: no limit.*

### Shipping

- [ ] **D3. First git commit.** Nothing is committed yet. *Default: Claude
  commits only when asked.*
- [ ] **D4. Push to GitHub and deploy to Streamlit Community Cloud.** Needs
  a GitHub account; steps are in README.md. Best done early, not on day 4.
  *Default: local only.*

### Agent behaviour

- [ ] **D5. Reply speed versus thoroughness.** Replies take 5–7 seconds at
  `EFFORT = "medium"`. `"low"` should be faster; not yet measured, and rule
  adherence at "low" is untested. *Default: medium.*
- [ ] **D6. Agent persona name.** *Default: "Azul" (placeholder).*
- [ ] **D7. Identity verification factors.** *Default: date of birth plus
  last 4 digits of the account number, 3 attempts, then handoff. All
  placeholders, not Banco Azteca's real process.*
- [ ] **D8. Compliance rules in the rulebook.** The boundaries in
  `rulebook/shared.md` (no threats, no third-party disclosure, and so on)
  are generic good practice. Check them against the rules that actually
  apply to collections conduct in Mexico as part of your business research.
  *Default: generic rules stay.*

### Use cases

- [ ] **D9. Final use cases.** Pending your business research. *Default:
  collections (payment promises) as module 1.*
- [ ] **D10. Second use case.** The take-home needs two end to end.
  *Default: a thin inbound account-support module at milestone 4, replaced
  once D9 is settled.*
- [ ] **D11. Changing a contact phone number.** This is an account-takeover
  risk in a real bank and would need stronger verification than D7.
  *Default: built as a simple placeholder tool in the collections module.*

### Demo

- [ ] **D12. Demo script and backup.** A rehearsed script with known
  customers, and a recorded backup video in case the live demo fails.
  *Default: none yet; revisit at milestone 5.*

### Environment

- [ ] **D13. Local Python version.** This Mac has Python 3.9, which pins an
  older version of the Anthropic library. Everything works. Upgrading to
  3.12 would match Streamlit Cloud. *Default: stay on 3.9.*

## Done

- [x] **Stack** (2026-10-02): Python, Claude API with a hand-written tool
  loop, SQLite, Streamlit. No agent framework.
- [x] **Who opens the collections conversation** (2026-10-02): the agent
  does (outbound), and says nothing about the debt until identity is
  verified.
- [x] **Project location** (2026-10-02): `~/yalo-azteca-agent`, a git repo.
- [x] **Passcode on the app** (2026-10-02): yes, via `APP_PASSCODE`.
- [x] **Design goal** (2026-10-02): a modular scaffold to tinker with; both
  initial modules are throwaway fixtures.
- [x] **Refusal fallback** (2026-10-02): on; confirmed working live.
- [x] **Model** (2026-10-02): `claude-opus-5-5`, set in `config.py`.
