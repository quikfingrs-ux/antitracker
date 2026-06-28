# Anti-Tracker — Product Spec v0.2
*Forge job #1 under Fab. Supersedes v0.1 (26 Jun 2026). Updated 27 Jun 2026.*
*STAGING COPY — lives in workspace\antitracker_staging\ until the `antitracker`
repo is created; then it moves into the repo as the canonical spec.*

---

## One line
An Android app that lets you use your phone **normally** while it quietly blocks
**data trafficking, ads, and trackers** any app gives out but doesn't need —
with **one-click setup**, a **"what broke?"** safety net so you're never left
stuck, and a **one-touch lockdown** to cut everything in and out. Lean on battery.

## Who it's for
Normal people who want privacy without becoming a network engineer. One app, one
tap, phone keeps working. **Not** the power user who'll pair three tools and read
a wiki.

---

## What's new in v0.2 (vs v0.1)
1. **Battery efficiency** promoted to a stated design target (with method, below).
2. **One-touch lockdown** added — a panic toggle that cuts all traffic in + out.
3. **Platform locked: Android-first.** iOS named explicitly as a *separate, later
   engine* (not a fork of this code). Play Store path confirmed unblocked.
4. **Monetization model** written down: open-source app, sold on convenience +
   optional paid service layer (GPL allows selling; it forbids closed-source).

---

## The gap — where today's blockers fall short
| Tool | Strength | Where it falls short |
|------|----------|----------------------|
| **NetGuard** | Reliable, no-root, lightweight | Minimal — per-app on/off; weak built-in ad/tracker filtering; pair with other tools |
| **AdGuard / Blokada** | Good ad/tracker blocking | Separate app; some features paid; no breakage diagnosis |
| **RethinkDNS** | Feature-rich (DNS, blocklists, proxy) | Powerful but fragile — breaks apps, confusing, users revert |
| **AFWall+** | Kernel-level precision | Needs root, steep learning curve |
| **TrackerControl** | Tracker visibility | Yet another tool to pair |

**The pattern:** full protection today = pairing 2–3 apps, fiddly setup, and when
something breaks you get **no clear answer why** — so people give up. Reliable
tools are minimal; powerful tools are fragile. **Nobody hits simple AND complete
AND self-healing.** That's the opening.

---

## What Anti-Tracker does (the wedge)
1. **One app, three jobs** — firewall + ad-block + tracker-block in one install.
2. **Self-setup** — one permission tap, then it configures itself. ⭐ *differentiator*
3. **"What broke?" safety net** — when a block stops an app working, it surfaces
   *which* block caused it + offers a one-tap allow. ⭐⭐ *headline differentiator*
4. **One-touch lockdown** — a single toggle cuts all traffic (panic / privacy
   mode). Mostly exposes NetGuard's existing lockdown capability. *(new v0.2)*
5. **Battery-lean by design** — see target below. *(new v0.2)*
6. **Normal use preserved** — conservative defaults + the safety net keep the
   phone working.
7. **No root. Android-first.**

---

## Battery efficiency (target, with method — not a promise) *(new v0.2)*
Filtering all traffic needs a persistent service, which always costs *some*
battery — "filter everything" and "zero drain" can't both be 100%. The goal is to
**minimise** it, honestly:
- Lean on NetGuard's already-efficient native filter loop (don't add fat).
- Minimise wakeups / avoid needless reloads on network changes.
- No analytics, no background phone-home (also the trust story).
- **Target:** negligible day-to-day drain in normal use; measured, not claimed,
  before we make any battery claim in the listing.

## One-touch lockdown (in + out) *(new v0.2)*
A single toggle that cuts all traffic — panic button / privacy moment.
- **Outbound: fully controlled** (no-root VPN slot owns all egress).
- **Inbound: limited on a no-root phone** — but phone traffic is almost entirely
  client-initiated outbound, so in practice this does what's wanted.
- Cheap to build: largely a UI surface over the base engine's lockdown mode.

---

## Platform — Android first, iOS a separate later engine *(locked v0.2)*
- **v1 = Android only.** Everything here (NetGuard fork, VpnService, on-device
  filtering) is Android. Google Play developer account: ✅ already held.
- **iOS is NOT this codebase.** iOS system-wide blocking uses Apple's
  NetworkExtension framework (Swift), needs a **Mac + $99/yr Apple account +
  App Store review**. It's a *second engine sharing the idea*, tackled after
  Android proves the loop. Weaker twin, later.

---

## Monetization — open-source AND sold *(new v0.2)*
GPLv3 (inherited from NetGuard) lets you **sell** the app; it forbids making it
**closed-source**. So revenue comes from things the licence can't lock, not from
code scarcity:
| Layer | Open/Closed | How it earns |
|-------|-------------|--------------|
| The app (NetGuard fork + our features) | GPLv3, public | Paid-for-convenience on Play Store; free on F-Droid |
| Optional backend service (later) | Ours, closed | Subscription — hosted blocklists / sync / premium filtering. GPL can't touch a service. |
- Honest limit: anyone can rebuild the public source and share it free — so we
  sell **convenience + trust + (optional) service**, not exclusivity. For a
  privacy app the open source IS the marketing ("read every line").
- *Not legal advice — a commercial launch deserves a proper licensing review.*

---

## Honest constraints (named, not hidden)
- **VPN-slot rule:** Android allows ONE local-VPN app at a time → can't run
  Anti-Tracker AND a separate full VPN together. (Every no-root blocker shares this.)
- **On-device only** — no traffic leaves to our servers; filtering is on the phone.
- **Battery** — some cost is unavoidable (see target).
- **Inbound lockdown** — limited without root (see lockdown).

## What it deliberately does NOT do (scope discipline)
- Not a full VPN, not anti-censorship tooling.
- Not for rooted power users chasing iptables precision (AFWall+'s lane).
- **No accounts, no cloud, no telemetry in the app itself.** (A tracker-blocker
  that phones home would be fatal — and it's the trust story.)

---

## Build basis
- **Fork NetGuard (GPLv3)** — proven local-VPN firewall engine. Don't rewrite the
  TCP/IP stack. Add ad/tracker blocklists + self-setup + "what broke?" + lockdown
  UI + battery polish on top.
- Ship **GPLv3**. Play Store (account ✅) is the goal; F-Droid the natural home.
- **Legal line:** studied the category, built our own on a GPL base — not copied.

---

## Phases (carry by hand first, automate later)
| Phase | Goal | Status |
|-------|------|--------|
| **1** | Skeleton + VPN proof (fork builds, slot acquired) | ⬜ next |
| **2** | Blocking — ads + trackers via blocklists | ⬜ |
| **3** | Self-setup — one tap configures it ⭐ | ⬜ |
| **4** | "What broke?" safety net ⭐⭐ | ⬜ |
| **5** | Dashboard — what got blocked, plainly shown (+ lockdown toggle, battery view) | ⬜ |
| **6** | Polish + ship (Play → F-Droid) | ⬜ |

*The two ⭐ rows (self-setup + "what broke?") are the whole reason this exists.
Lockdown + battery are differentiator polish on top. Everything else, the
competition already does. Build the ⭐ rows well and it's a real product.*
