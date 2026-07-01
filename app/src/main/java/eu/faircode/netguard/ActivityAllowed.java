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

import android.os.Bundle;
import android.view.MenuItem;
import android.view.View;
import android.widget.ListView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

public class ActivityAllowed extends AppCompatActivity implements AdapterAllowed.OnUndoListener {
    private AdapterAllowed adapter = null;
    private ListView lvAllowed;
    private TextView tvIntro;
    private TextView tvEmpty;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        Util.setTheme(this);
        super.onCreate(savedInstanceState);
        setContentView(R.layout.allowed);

        getSupportActionBar().setTitle(R.string.title_allowed);
        getSupportActionBar().setDisplayHomeAsUpEnabled(true);

        tvIntro = findViewById(R.id.tvIntro);
        tvEmpty = findViewById(R.id.tvEmpty);
        lvAllowed = findViewById(R.id.lvAllowed);
        lvAllowed.setEmptyView(tvEmpty);

        adapter = new AdapterAllowed(this, DatabaseHelper.getInstance(this).getAllowed(), this);
        lvAllowed.setAdapter(adapter);

        updateIntro();
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == android.R.id.home) {
            finish();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    @Override
    public void onUndo() {
        updateAdapter();
    }

    private void updateAdapter() {
        if (adapter != null) {
            adapter.changeCursor(DatabaseHelper.getInstance(this).getAllowed());
            updateIntro();
        }
    }

    private void updateIntro() {
        if (tvIntro != null && adapter != null)
            tvIntro.setVisibility(adapter.getCount() > 0 ? View.VISIBLE : View.GONE);
    }

    @Override
    protected void onDestroy() {
        adapter = null;
        super.onDestroy();
    }
}
