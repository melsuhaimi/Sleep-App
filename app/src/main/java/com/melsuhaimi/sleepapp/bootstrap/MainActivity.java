package com.melsuhaimi.sleepapp.bootstrap;

import android.app.Activity;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.TextView;

public final class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        TextView view = new TextView(this);
        view.setGravity(Gravity.CENTER);
        view.setText(CheckpointContract.SCREEN_TEXT);
        view.setTextSize(24f);
        setContentView(view);
    }
}
