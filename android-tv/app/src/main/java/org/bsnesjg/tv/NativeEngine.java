package org.bsnesjg.tv;

import android.content.res.AssetManager;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;

final class NativeEngine {
    static { System.loadLibrary("bjg"); }
    static native boolean load(AssetManager assets, byte[] rom, String romName);
    static native boolean isLoaded();
    static native void step();
    static native long benchmark(int frames);
    static native void reset();
    static native void setPad(int mask);
    static native int width();
    static native int height();
    static native int pitch();
    static native void copyPixels(java.nio.ByteBuffer pixels);
    static native int wramWord(int offset);
    static byte[] read(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] buf = new byte[32768];
        for (int n; (n = in.read(buf)) >= 0;) out.write(buf, 0, n);
        return out.toByteArray();
    }
    private NativeEngine() {}
}
