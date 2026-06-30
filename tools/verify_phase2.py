#!/usr/bin/env python3
"""
verify_phase2.py  --  Anti-Tracker Phase 2 end-to-end blocking verifier.

WHAT THIS IS
    The executable definition of "Phase 2 passes": a list of domains that MUST be
    blocked (ads/trackers) and a list of controls that MUST still resolve (over-block
    guard). Drives an Android emulator headlessly via adb -- no mouse, no tapping.

    Reused across phases: later phases swap MUST_BLOCK / MUST_RESOLVE and reuse the rig.

HOW IT WORKS (debug build only -- relies on run-as, which needs a debuggable app)
    1. (optional) build      gradlew assembleDebug
    2. (optional) install     adb install -r app-debug.apk
    3. force-stop the app     (so it can't clobber prefs on exit)
    4. set prefs              filter=true, use_hosts=true, enabled=true   (via run-as)
    5. provide a blocklist
         push     mode: write a controlled hosts.txt of MUST_BLOCK domains (deterministic)
         download mode: trigger ServiceExternal -> fetches the REAL StevenBlack default
    6. start the tunnel       adb reboot -> ReceiverAutostart sees enabled=true -> VPN up
                              (VPN consent must have been granted ONCE beforehand; it
                               persists across reboot as long as the app isn't uninstalled)
    7. assert DNS             ping each domain, read the resolved IP:
                              blocked  == 0.0.0.0 / unresolved ;  resolved == real IP
    8. print PASS/FAIL table, exit 0 (all pass) or 1 (any fail)

ONE-TIME MANUAL STEP (per AVD)
    Launch the app once, tap to grant the VPN-consent dialog. After that this script
    is hands-off. Snapshot the AVD afterwards if you want a clean cold baseline.

USAGE
    python tools/verify_phase2.py                 # push mode, assert only (assumes installed)
    python tools/verify_phase2.py --build --install
    python tools/verify_phase2.py --mode download # test the real StevenBlack default
"""

import argparse
import os
import re
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# THE SPEC  --  this block is what "Phase 2 success" means. Edit here, not in code.
# ---------------------------------------------------------------------------
PACKAGE = "uk.fab.antitracker"

MUST_BLOCK = [          # ad / tracker domains -- all present in StevenBlack unified
    "doubleclick.net",
    "google-analytics.com",
    "googlesyndication.com",
    "app-measurement.com",      # Firebase Analytics -- the classic mobile tracker
    "adservice.google.com",
]
MUST_RESOLVE = [        # controls -- must NOT be blocked (catches over-blocking)
    "wikipedia.org",
    "github.com",
    "cloudflare.com",
    "example.com",
]

# Real shipped default we want to prove in --mode download (placeholder triggers the
# BuildConfig.HOSTS_FILE_URI swap in ServiceExternal -> StevenBlack unified).
HOSTS_URL_PLACEHOLDER = "https://www.netguard.me/hosts"

# ---------------------------------------------------------------------------
# paths / env
# ---------------------------------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFS_FILE = f"/data/data/{PACKAGE}/shared_prefs/{PACKAGE}_preferences.xml"
HOSTS_DEVICE = f"/data/data/{PACKAGE}/files/hosts.txt"
DEBUG_DIR = os.path.join(REPO, "app", "build", "outputs", "apk", "debug")


def find_debug_apk():
    """Gradle renames the debug output (e.g. NetGuard-v2.335-debug.apk), so glob
    for the newest *-debug.apk rather than assuming app-debug.apk."""
    import glob
    apks = glob.glob(os.path.join(DEBUG_DIR, "*-debug.apk"))
    apks.sort(key=os.path.getmtime, reverse=True)
    return apks[0] if apks else os.path.join(DEBUG_DIR, "app-debug.apk")

# Laptop build gotchas (see charter): JAVA_HOME -> Android Studio jbr if not already set.
JBR = r"C:\Program Files\Android\Android Studio\jbr"

PREFS_TEMPLATE = "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n</map>\n"


def find_adb():
    for env in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        root = os.environ.get(env)
        if root:
            cand = os.path.join(root, "platform-tools", "adb.exe")
            if os.path.exists(cand):
                return cand
    local = os.environ.get("LOCALAPPDATA")
    if local:
        cand = os.path.join(local, "Android", "Sdk", "platform-tools", "adb.exe")
        if os.path.exists(cand):
            return cand
    return "adb"   # fall back to PATH


ADB = find_adb()


def adb(*args, **kw):
    """Run adb, return CompletedProcess. input= pipes bytes to remote stdin."""
    return subprocess.run([ADB, *args], capture_output=True, **kw)


def adb_out(*args):
    return adb(*args).stdout.decode("utf-8", "replace")


def shell(cmd):
    return adb_out("shell", cmd)


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# device readiness
# ---------------------------------------------------------------------------
def wait_for_device(timeout=120):
    log("  waiting for device...")
    adb("wait-for-device")
    t0 = time.time()
    while time.time() - t0 < timeout:
        if shell("getprop sys.boot_completed").strip() == "1":
            return True
        time.sleep(2)
    return False


def device_present():
    out = adb_out("get-state").strip()
    return out == "device"


# ---------------------------------------------------------------------------
# device data access — via ROOT (this AVD is userdebug; run-as is SELinux-blocked
# for writes, so we write as root then chown + restorecon so the file lands
# app-owned with the right label, exactly as if the app had created it)
# ---------------------------------------------------------------------------
_app_uid = [None]


def enable_root():
    out = adb_out("root").strip()
    time.sleep(2)
    adb("wait-for-device")
    return "cannot run as root" not in out.lower()


def app_uid():
    if _app_uid[0] is None:
        _app_uid[0] = adb_out("shell", "stat", "-c", "%u",
                              f"/data/data/{PACKAGE}").strip() or "0"
    return _app_uid[0]


def dev_read(path):
    return adb_out("shell", "cat", path)   # root can read


def dev_write(path, content):
    """Write a file as root, then hand it to the app uid with the correct
    SELinux label so the app can read/write it as its own."""
    r = adb("shell", "sh", "-c", f"cat > {path}", input=content.encode("utf-8"))
    if r.returncode != 0:
        log("  ! write failed: " + r.stderr.decode("utf-8", "replace").strip())
        return False
    uid = app_uid()
    adb("shell", "chown", f"{uid}:{uid}", path)
    adb("shell", "chmod", "660", path)
    adb("shell", "restorecon", path)
    return True


def read_prefs():
    out = dev_read(PREFS_FILE)
    return out if "<map>" in out else PREFS_TEMPLATE


def write_prefs(xml):
    return dev_write(PREFS_FILE, xml)


def set_bool(xml, key, val):
    pat = re.compile(rf'<boolean name="{re.escape(key)}" value="(?:true|false)" ?/>')
    repl = f'<boolean name="{key}" value="{str(val).lower()}" />'
    if pat.search(xml):
        return pat.sub(repl, xml, count=1)
    return xml.replace("</map>", f"    {repl}\n</map>")


def set_string(xml, key, value):
    pat = re.compile(rf'<string name="{re.escape(key)}">.*?</string>', re.S)
    repl = f"<string name=\"{key}\">{value}</string>"
    if pat.search(xml):
        return pat.sub(repl, xml, count=1)
    return xml.replace("</map>", f"    {repl}\n</map>")


def configure_prefs(download_mode):
    log("  setting prefs (filter, use_hosts, enabled)...")
    xml = read_prefs()
    xml = set_bool(xml, "filter", True)
    xml = set_bool(xml, "use_hosts", True)
    xml = set_bool(xml, "enabled", True)
    if download_mode:
        # placeholder -> ServiceExternal swaps to BuildConfig.HOSTS_FILE_URI (StevenBlack)
        xml = set_string(xml, "hosts_url", HOSTS_URL_PLACEHOLDER)
    return write_prefs(xml)


# ---------------------------------------------------------------------------
# blocklist provisioning
# ---------------------------------------------------------------------------
def push_controlled_hosts():
    log("  pushing controlled hosts.txt (MUST_BLOCK domains)...")
    content = "# Anti-Tracker Phase 2 controlled test list\n" + \
              "\n".join(f"0.0.0.0 {d}" for d in MUST_BLOCK) + "\n"
    return dev_write(HOSTS_DEVICE, content)


def trigger_download(timeout=90):
    log("  triggering ServiceExternal DOWNLOAD_HOSTS_FILE (real StevenBlack default)...")
    adb("shell", "am", "start-service", "-a",
        "eu.faircode.netguard.DOWNLOAD_HOSTS_FILE", "-n",
        f"{PACKAGE}/eu.faircode.netguard.ServiceExternal")
    t0 = time.time()
    while time.time() - t0 < timeout:
        size = adb("shell", "run-as", PACKAGE, "sh", "-c",
                   f"wc -c < {HOSTS_DEVICE} 2>/dev/null").stdout.decode().strip()
        if size.isdigit() and int(size) > 10000:   # StevenBlack is multi-MB
            log(f"    downloaded {int(size):,} bytes")
            return True
        time.sleep(3)
    log("    ! download did not complete (network? check logcat NetGuard.External)")
    return False


# ---------------------------------------------------------------------------
# tunnel
# ---------------------------------------------------------------------------
def start_tunnel(settle=18):
    log("  rebooting AVD so ReceiverAutostart brings the VPN up (enabled=true)...")
    adb("reboot")
    time.sleep(4)
    if not wait_for_device():
        log("  ! device did not finish booting")
        return False
    log(f"  boot complete; letting the tunnel settle ({settle}s)...")
    time.sleep(settle)
    services = shell(f"dumpsys activity services {PACKAGE}")
    up = "ServiceSinkhole" in services
    log("  tunnel service: " + ("running" if up else "NOT detected"))
    if not up:
        # self-diagnose: dump NetGuard's own log so a failure explains itself
        lg = shell("logcat -d -t 600")
        ng = [l for l in lg.splitlines()
              if "netguard" in l.lower() or "vpn" in l.lower()]
        log("  --- NetGuard/VPN logcat (why the tunnel didn't start) ---")
        log("\n".join(ng[-25:]) if ng else "  (no NetGuard/VPN log lines found)")
        log("  appops ACTIVATE_VPN: " + shell(f"appops get {PACKAGE} ACTIVATE_VPN").strip())
    return True


# ---------------------------------------------------------------------------
# DNS assertion
# ---------------------------------------------------------------------------
def resolve_ip(domain):
    out = shell(f"ping -c 1 -W 1 {domain}")
    m = re.search(r"PING [^ ]+ \(([0-9.]+)\)", out)
    if m:
        return m.group(1)
    return None   # unknown host / unresolved


def assert_domains():
    log("\n  asserting DNS...\n")
    rows, ok = [], True

    for d in MUST_BLOCK:
        ip = resolve_ip(d)
        blocked = ip in (None, "0.0.0.0")
        ok = ok and blocked
        rows.append(("BLOCK", d, ip or "unresolved", "PASS" if blocked else "FAIL"))

    for d in MUST_RESOLVE:
        ip = resolve_ip(d)
        resolved = ip not in (None, "0.0.0.0")
        ok = ok and resolved
        rows.append(("ALLOW", d, ip or "unresolved", "PASS" if resolved else "FAIL"))

    w = max(len(r[1]) for r in rows)
    print(f"  {'want':<6} {'domain':<{w}}  {'resolved':<16} result")
    print(f"  {'-'*6} {'-'*w}  {'-'*16} ------")
    for want, dom, ip, res in rows:
        mark = "ok " if res == "PASS" else ">> "
        print(f"  {mark}{want:<3} {dom:<{w}}  {ip:<16} {res}")
    return ok


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Anti-Tracker Phase 2 verifier")
    ap.add_argument("--mode", choices=("push", "download"), default="push",
                    help="push=controlled list (deterministic); download=real StevenBlack default")
    ap.add_argument("--build", action="store_true", help="gradlew assembleDebug first")
    ap.add_argument("--install", action="store_true", help="adb install -r the debug APK")
    ap.add_argument("--apk", default=None, help="explicit APK path; default = newest *-debug.apk")
    ap.add_argument("--setup-only", action="store_true",
                    help="build/install then STOP (so you can grant VPN consent) before verifying")
    ap.add_argument("--settle", type=int, default=18, help="seconds to let the tunnel settle after boot")
    ap.add_argument("--diag", action="store_true", help="print device/run-as/root diagnostics and exit")
    ap.add_argument("--blockdiag", action="store_true",
                    help="tunnel already up: dump prefs + hosts + NetGuard hosts/filter log, then exit")
    ap.add_argument("--canary", action="store_true",
                    help="tunnel up: probe NetGuard canary + our domains + routing (no reboot)")
    args = ap.parse_args()

    if args.canary:
        adb("wait-for-device")
        log("[canary] (tunnel assumed up from a prior run)")
        for d in ("test.netguard.me", "doubleclick.net", "google-analytics.com", "wikipedia.org"):
            log(f"  {d:24} -> {resolve_ip(d)}")
        log("--- ip rule ---\n" + shell("ip rule").strip())
        log("--- ip route (default) ---\n" +
            "\n".join(l for l in shell("ip route").splitlines() if "default" in l or "tun" in l))
        log("--- getprop net.dns1 ---\n" + shell("getprop net.dns1").strip())
        return 0

    log(f"ADB: {ADB}")
    log(f"Package: {PACKAGE}   Mode: {args.mode}\n")

    if args.diag:
        adb("wait-for-device")
        log("[diag]")
        log("ro.build.type : " + shell("getprop ro.build.type").strip())
        log("ro.debuggable  : " + shell("getprop ro.debuggable").strip())
        log("adb root       : " + adb_out("root").strip())
        time.sleep(2); adb("wait-for-device")
        log("id (shell)     : " + shell("id").strip())
        log("run-as id      : " + adb_out("shell", "run-as", PACKAGE, "id").strip())
        log("pm path        : " + shell(f"pm path {PACKAGE}").strip())
        log("ls data dir    :\n" + adb_out("shell", "run-as", PACKAGE, "ls", "-la", f"/data/data/{PACKAGE}").strip())
        return 0

    if args.blockdiag:
        adb("wait-for-device")
        enable_root()
        log("[blockdiag]  (tunnel assumed up from a prior run)")
        log("--- prefs on device ---")
        log(dev_read(PREFS_FILE).strip())
        log("--- hosts.txt on device ---")
        log(shell(f"wc -l {HOSTS_DEVICE}").strip())
        log(dev_read(HOSTS_DEVICE).strip()[:400])
        log("--- ServiceSinkhole running? ---")
        log("ServiceSinkhole" if "ServiceSinkhole" in shell(f"dumpsys activity services {PACKAGE}") else "no")
        log("--- NetGuard logcat (hosts/filter/blocked) ---")
        lg = shell("logcat -d -t 1500")
        keep = [l for l in lg.splitlines()
                if any(k in l.lower() for k in ("hosts", "sinkhole", "filtering", "blocked", "loaded", "allowed "))]
        log("\n".join(keep[-35:]) if keep else "  (no matching log lines)")
        return 0

    if args.build:
        log("[build] gradlew assembleDebug")
        env = dict(os.environ)
        if not env.get("JAVA_HOME") and os.path.exists(JBR):
            env["JAVA_HOME"] = JBR
            log(f"  (JAVA_HOME -> {JBR})")
        gradlew = os.path.join(REPO, "gradlew.bat")
        r = subprocess.run([gradlew, "assembleDebug"], cwd=REPO, env=env)
        if r.returncode != 0:
            log("! build failed"); return 2

    if not device_present():
        log("! no emulator/device. Start your AVD first."); return 2
    wait_for_device()

    if args.install:
        apk = args.apk or find_debug_apk()
        log(f"[install] {apk}")
        r = adb("install", "-r", apk)
        out = (r.stdout + b"\n" + r.stderr).decode("utf-8", "replace").strip()
        log("  " + out)
        if b"Success" not in r.stdout:
            log("! install failed (see adb output above)")
            log(f"  if signature mismatch:  adb uninstall {PACKAGE}  then re-run")
            return 2

    if args.setup_only:
        log("\n[setup-only] APK is on the device.")
        log("  Now: open Anti-Tracker, tap to enable it, accept the VPN")
        log("  'Connection request' dialog ONCE. Then re-run WITHOUT --setup-only.")
        return 0

    log("[configure]")
    rooted = enable_root()
    log("  root: " + ("yes" if rooted else "NO — writes will fail on a production image"))
    adb("shell", "am", "force-stop", PACKAGE)
    # Ensure the app's data dirs exist + are app-owned with the right SELinux label
    # (done as root; the file writes below also chown/restorecon).
    uid = app_uid()
    for d in (f"/data/data/{PACKAGE}/shared_prefs", f"/data/data/{PACKAGE}/files"):
        adb("shell", "mkdir", "-p", d)
        adb("shell", "chown", f"{uid}:{uid}", d)
        adb("shell", "restorecon", "-R", d)
    # Pre-grant VPN consent headlessly so ReceiverAutostart can raise the tunnel
    # silently after the reboot (no manual "Connection request" tap).
    adb("shell", "appops", "set", PACKAGE, "ACTIVATE_VPN", "allow")
    # NetGuard hosts-blocking only sees PLAINTEXT DNS — Android's Private DNS (DoT)
    # encrypts queries and bypasses the sinkhole. Force it off for the test.
    adb("shell", "settings", "put", "global", "private_dns_mode", "off")
    if not configure_prefs(args.mode == "download"):
        log("! could not set prefs (need root or a debuggable build)"); return 2

    if args.mode == "push":
        if not push_controlled_hosts():
            log("! could not push hosts.txt"); return 2
    else:
        if not trigger_download():
            return 2

    log("[tunnel]")
    if not start_tunnel(args.settle):
        return 2

    ok = assert_domains()
    print("\n  " + ("=== PHASE 2 PASS ===" if ok else "=== PHASE 2 FAIL ==="))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
