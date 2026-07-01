package eu.faircode.netguard;

/*
    This file is part of NetGuard.

    NetGuard is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    NetGuard is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with NetGuard.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2015-2026 by Marcel Bokhorst (M66B)
*/

import android.content.Context;
import android.database.Cursor;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CursorAdapter;
import android.widget.TextView;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class AdapterAllowed extends CursorAdapter {
    public interface OnUndoListener {
        void onUndo();
    }

    private final int colId;
    private final int colUid;
    private final int colDaddr;
    private final Map<Integer, String> nameCache = new HashMap<>();
    private final OnUndoListener listener;

    public AdapterAllowed(Context context, Cursor cursor, OnUndoListener listener) {
        super(context, cursor, 0);
        this.listener = listener;
        colId = cursor.getColumnIndexOrThrow("_id");
        colUid = cursor.getColumnIndexOrThrow("uid");
        colDaddr = cursor.getColumnIndexOrThrow("daddr");
    }

    @Override
    public View newView(Context context, Cursor cursor, ViewGroup parent) {
        return LayoutInflater.from(context).inflate(R.layout.allowed_item, parent, false);
    }

    @Override
    public void bindView(View view, final Context context, Cursor cursor) {
        final long id = cursor.getLong(colId);
        int uid = cursor.getInt(colUid);
        String host = cursor.getString(colDaddr);

        TextView tvApp = view.findViewById(R.id.tvApp);
        TextView tvHost = view.findViewById(R.id.tvHost);
        Button btnUndo = view.findViewById(R.id.btnUndo);

        tvApp.setText(getAppName(context, uid));
        tvHost.setText(host);

        btnUndo.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                DatabaseHelper.getInstance(context).setAccess(id, 1);
                ServiceSinkhole.reload("shutter undo allow", context, false);
                if (listener != null)
                    listener.onUndo();
            }
        });
    }

    private String getAppName(Context context, int uid) {
        String cached = nameCache.get(uid);
        if (cached != null)
            return cached;

        List<String> names = Util.getApplicationNames(uid, context);
        String label;
        if (names == null || names.isEmpty())
            label = "uid " + uid;
        else
            label = names.get(0);

        nameCache.put(uid, label);
        return label;
    }
}
