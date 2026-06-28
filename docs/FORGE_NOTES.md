# Forge / Anti-Tracker — Build Notes
*Living guiding notes for the build. Not a log — revise in place.*
*Started 27 Jun 2026.*

---

## Guiding principles

### P1 — Race to the ⭐⭐ features. Don't over-build the firewall.
NetGuard already solved the hard part (the on-device packet-filter engine).
Phases 1–2 (build + blocklists) are **table stakes** — every competitor has them.
The product only actually exists in **self-setup ⭐** and **"what broke?" ⭐⭐**.
The standing temptation (especially with an eager executor) is to keep polishing a
firewall that's already done. Resist it. Get a thin, even ugly version of the two
⭐ features working as fast as possible — that's the only real validation of the
whole bet. Polish the engine LAST, not first.

---

## Watch-outs / dependency risks

### W1 — NetGuard is essentially one maintainer.
We've forked a solo-maintained project (Marcel Bokhorst / M66B). That's fine, but
eyes-open: if upstream goes quiet, we inherit the *entire* thing — including the
**native C packet filter (NDK)**, which is the gnarliest part of the codebase and
the bit we're least equipped to maintain. Mitigation isn't urgent, but: keep the
`upstream-baseline` tag + a clean diff so we always know exactly what's ours vs
upstream, and don't let our changes tangle into the native layer unless we have to.

---

## Open strategic threads (NOT settled — revisit, don't treat as decided)

### T2 — What is the paid service? (the real moat)
GPL means code isn't a moat — anyone can fork us like we forked NetGuard. The moat
is trust + curated blocklists + the "what broke" UX + **a paid service layer**.
Worth roughing out *what that service actually is* (hosted/curated blocklists?
sync? premium filtering?) before too long, because it may shape hooks the app
needs early. Decision pending — not built into any phase yet.

### T3 — Validate appetite cheaply before the heavy ⭐⭐ build.
The core bet is "one-tap setup + never-left-stuck." Testable for ~£0: a landing
page, a temperature-check in r/privacy / r/androidapps on the specific "what broke?"
idea, or mining what NetGuard/Blokada users actually complain about. Could save
weeks if the bet's wrong, or sharpen it if it's right. Optional — flagged as
high-leverage, but it's Paul's call whether to validate-first or just build.
