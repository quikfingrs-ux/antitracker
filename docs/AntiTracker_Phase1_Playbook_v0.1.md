# Anti-Tracker — Phase 1 Playbook v0.1
*Forge job #1 under Fab. Skeleton + VPN proof. Drafted 27 Jun 2026.*
*Carry by hand first — feel the pain, automate later.*

---

## Goal (Phase 1 definition of done — the gate)
Our fork of NetGuard:
1. **Builds** a debug APK from clean source on the chosen machine (toolchain
   proven against the real native/NDK code).
2. **Installs** under *our own* `applicationId`, alongside a stock NetGuard.
3. **Acquires the VPN slot** and filters traffic — block one app, confirm it's
   cut off; allow it, confirm it's back. That's "slot acquired".
4. **Repo is ours**, GPLv3 intact, **first commit = pristine upstream** (tagged
   `upstream-baseline`), so every later change of ours is a visible diff.

When all four are true → Phase 1 green → Phase 2 (ad/tracker blocklists) opens.

---

## Fork basis (confirmed 27 Jun 2026)
- Upstream: **github.com/M66B/NetGuard**, **GPLv3** ("and will always be").
- Current ~**v2.334**, Android 15+ ready, actively maintained.
- Stock package id: `eu.faircode.netguard`.
- **Has a native C component built via the NDK** (the packet filter) — toolchain
  needs NDK + CMake, not just the SDK. This is the main build-pain risk.
- Repo cloned to `C:\Users\paul\antitracker\` (PC) + laptop clone. Baseline tagged
  `upstream-baseline`. Wired into the MCP (allowed_roots + GIT_REPOS).

---

## Decisions (locked 27 Jun 2026)
| # | Decision | Locked |
|---|----------|--------|
| D1 | Code home / Cefn edit access | **main-PC MCP-editable project** (Git-shared with laptop) |
| D2 | Build machine | **either** — PC and laptop both full dev boxes |
| D3 | VPN-proof target | **AVD emulator** (no physical Android phone) |
| D4 | Package id | **rename** (e.g. `uk.fab.antitracker`) — installs alongside |
| D5 | Build hands | **Paul's-hands now** (prove by hand); runner later if needed |

---

## Sequence
| Step | What | Hands |
|------|------|-------|
| 1 | **Toolchain**: JDK 17, Android Studio (✅ installed), SDK (API 35), **+ NDK + CMake**, **+ an AVD**. Confirm `assembleDebug` works on a throwaway project. | Paul |
| 2 | **Fork + clone** — ✅ DONE. Repo `quikfingrs-ux/antitracker`, pristine NetGuard tagged `upstream-baseline`, cloned PC + laptop. | ✅ |
| 3 | **Baseline build, UNMODIFIED**: open in Android Studio, Gradle sync, `assembleDebug`. APK out = toolchain proven against the real native code *before* we change a line. | Paul (gradlew) |
| 4 | **Rename `applicationId`** in `app/build.gradle` so it installs beside stock NetGuard. Rebuild. | Cefn edits / Paul builds |
| 5 | **VPN proof**: install on the AVD, grant the VPN permission, enable filtering, block one app → confirm cut off, allow → confirm restored. Baseline green. | Paul (emulator) |
| 6 | **GPLv3 hygiene**: keep upstream LICENSE, add a NOTICE crediting Marcel Bokhorst / NetGuard + our changes. Tag the baseline (`p1-baseline`). | Cefn drafts |

---

## Hands split (who can do what)
**Paul's-hands only** (credential / install / device — Cefn never does these):
toolchain install, GitHub push, APK signing, running gradlew, the AVD.

**Cefn (via MCP)**: read + edit the fork's source, prepare the `applicationId`
rename, draft the NOTICE/attribution, scaffold Phase 2 blocklist plumbing, run
`git status/diff/add/commit` (push stays Paul's-hands — SYSTEM has no git creds).

---

## Risks / watch-outs
- **NDK build is the likely snag** — native toolchain version mismatches are the
  classic first-build failure. Step 3 (build unmodified first) isolates that from
  any change of ours.
- **VPN-slot rule**: only one app holds the local-VPN slot. Anti-Tracker can't run
  alongside a separate full VPN. Expected; not a bug.
- **Don't build the factory yet** — no cockpit app-factory tooling until this app
  is carried through by hand and we've felt where the pain is.

---

## After Phase 1
Phase 2 = ad/tracker blocking via blocklists (the first real *us* feature on top
of the firewall). Phases 3–4 (self-setup ⭐ and "what broke?" ⭐⭐) are the two
that justify the whole product — everything before them is table-stakes.
