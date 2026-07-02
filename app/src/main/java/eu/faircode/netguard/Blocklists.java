package eu.faircode.netguard;

/*
    This file is part of Shutter (a NetGuard GPLv3 fork).

    Shutter is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Based on NetGuard, Copyright 2015-2026 by Marcel Bokhorst (M66B).
*/

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;

import androidx.preference.PreferenceManager;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;

/**
 * Shutter blocklist strength picker.
 *
 * One simple choice — Light / Balanced / Strict — over free, curated HaGeZi public
 * lists in hosts format (0.0.0.0 &lt;domain&gt; per line, exactly what ServiceSinkhole
 * already parses). This replaces NetGuard's toggle-wall of individual host-file
 * settings with a single legible dial.
 *
 *   LIGHT    -> HaGeZi Light  (~110k domains, ~2.8 MB) — BUNDLED in the APK as the
 *                             offline default, so a fresh install blocks from tap one.
 *   BALANCED -> HaGeZi Normal (~500k domains, ~13 MB) — downloaded on demand.
 *   STRICT   -> HaGeZi Pro++  (~700k domains, ~18 MB) — downloaded on demand. The
 *                             Phase-4 "what broke?" safety net is what makes this
 *                             aggressive tier survivable for a normal user.
 *
 * The engine only ever reads a single hosts.txt in getFilesDir(); this class just
 * decides what fills it.
 */
public class Blocklists {
    private static final String TAG = "Shutter.Blocklists";

    public static final String PREF = "blocklist_strength";
    public static final String LIGHT = "light";
    public static final String BALANCED = "balanced";
    public static final String STRICT = "strict";
    public static final String DEFAULT = LIGHT;

    private static final String ASSET_LIGHT = "blocklist_light.txt";

    // HaGeZi hosts-format lists. Verified 200 + hosts format 2 Jul 2026.
    private static final String URL_BALANCED =
            "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts/multi.txt";
    private static final String URL_STRICT =
            "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts/pro.plus.txt";

    public static String current(Context context) {
        return PreferenceManager.getDefaultSharedPreferences(context).getString(PREF, DEFAULT);
    }

    /** URL for a downloadable tier, or null for LIGHT (which ships bundled). */
    public static String urlFor(String tier) {
        if (STRICT.equals(tier)) return URL_STRICT;
        if (BALANCED.equals(tier)) return URL_BALANCED;
        return null;
    }

    private static File hostsFile(Context context) {
        return new File(context.getFilesDir(), "hosts.txt");
    }

    /**
     * Seed the bundled Light list into hosts.txt if it's missing (first run, or after
     * a data-clear) so blocking works offline from the very first enable. Idempotent
     * and cheap — a no-op once hosts.txt exists. Safe to call from ApplicationEx.
     */
    public static void ensureSeeded(Context context) {
        File hosts = hostsFile(context);
        if (hosts.exists() && hosts.length() > 0)
            return;
        if (copyAsset(context, ASSET_LIGHT, hosts)) {
            Log.i(TAG, "Seeded hosts.txt from bundled Light (" + hosts.length() + " bytes)");
            SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(context);
            if (!prefs.contains(PREF))
                prefs.edit().putString(PREF, LIGHT).apply();
        }
    }

    public interface ApplyListener {
        void onApplied(String tier);

        void onFailed(String tier, Throwable ex);
    }

    /**
     * Apply a chosen tier. Writes the strength pref + ensures use_hosts is on, then:
     *   LIGHT             — copy the bundled asset over hosts.txt (instant, offline);
     *   BALANCED / STRICT — download the HaGeZi list, swap it into hosts.txt, reload.
     * The engine is reloaded on success so the new list takes effect immediately.
     */
    public static void apply(final Activity activity, final String tier, final ApplyListener listener) {
        final Context context = activity.getApplicationContext();
        PreferenceManager.getDefaultSharedPreferences(context)
                .edit()
                .putString(PREF, tier)
                .putBoolean("use_hosts", true)
                .apply();

        if (LIGHT.equals(tier)) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    final boolean ok = copyAsset(context, ASSET_LIGHT, hostsFile(context));
                    activity.runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            if (ok) {
                                ServiceSinkhole.reload("blocklist light", context, false);
                                listener.onApplied(tier);
                            } else
                                listener.onFailed(tier, new RuntimeException("asset copy failed"));
                        }
                    });
                }
            }).start();
            return;
        }

        // BALANCED / STRICT — download to a temp file, then atomically swap in.
        final File tmp = new File(context.getFilesDir(), "hosts.tmp");
        final File hosts = hostsFile(context);
        try {
            new DownloadTask(activity, new URL(urlFor(tier)), tmp, new DownloadTask.Listener() {
                @Override
                public void onCompleted() {
                    if (hosts.exists())
                        hosts.delete();
                    if (tmp.renameTo(hosts)) {
                        ServiceSinkhole.reload("blocklist " + tier, context, false);
                        listener.onApplied(tier);
                    } else
                        listener.onFailed(tier, new RuntimeException("hosts swap failed"));
                }

                @Override
                public void onCancelled() {
                    listener.onFailed(tier, new RuntimeException("download cancelled"));
                }

                @Override
                public void onException(Throwable ex) {
                    listener.onFailed(tier, ex);
                }
            }).execute();
        } catch (Throwable ex) {
            listener.onFailed(tier, ex);
        }
    }

    private static boolean copyAsset(Context context, String asset, File dst) {
        InputStream in = null;
        OutputStream out = null;
        try {
            in = context.getAssets().open(asset);
            out = new FileOutputStream(dst);
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) != -1)
                out.write(buf, 0, n);
            return true;
        } catch (Throwable ex) {
            Log.e(TAG, "copyAsset(" + asset + ") failed: " + ex);
            return false;
        } finally {
            try {
                if (in != null) in.close();
            } catch (Throwable ignored) {
            }
            try {
                if (out != null) out.close();
            } catch (Throwable ignored) {
            }
        }
    }
}
