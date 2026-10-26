package org.bsnesjg.tv;

import android.content.Intent;
import android.os.Bundle;

/** Coordinator-only entry point that launches the fixed Mandelbrot workload directly. */
public final class MandelbrotBenchmarkActivity extends MainActivity {
    @Override
    protected void onCreate(Bundle state) {
        Intent launch = new Intent(getIntent());
        launch.putExtra("rom", "mandel-display");
        setIntent(launch);
        super.onCreate(state);
    }
}
