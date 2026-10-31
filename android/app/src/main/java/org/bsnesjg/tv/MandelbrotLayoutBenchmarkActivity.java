package org.bsnesjg.tv;

import android.os.Bundle;

/** Freeze the canonical frame so hardware screenshots can be compared directly. */
public class MandelbrotLayoutBenchmarkActivity extends MandelbrotBenchmarkActivity {
    @Override
    protected void onCreate(Bundle state) {
        getIntent().putExtra("layoutProof", true);
        super.onCreate(state);
    }
}
