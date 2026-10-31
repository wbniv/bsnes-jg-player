package org.bsnesjg.tv;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileNotFoundException;

/** Grants a receiving share target temporary read access to this app's installed APK. */
public final class ApkShareProvider extends ContentProvider {
    private static final String MIME_TYPE = "application/vnd.android.package-archive";

    private File apkFile() throws FileNotFoundException {
        if (getContext() == null) throw new FileNotFoundException("Application context unavailable");
        File file = new File(getContext().getApplicationInfo().sourceDir);
        if (!file.isFile() || !file.canRead()) throw new FileNotFoundException("Installed APK unavailable");
        return file;
    }

    private void requireApkUri(Uri uri) throws FileNotFoundException {
        if (uri == null || getContext() == null
                || !((getContext().getPackageName() + ".apkshare").equals(uri.getAuthority()))
                || !"/app.apk".equals(uri.getPath())) {
            throw new FileNotFoundException("Unknown APK share URI");
        }
    }

    @Override public boolean onCreate() { return true; }

    @Override public String getType(Uri uri) {
        try {
            requireApkUri(uri);
            return MIME_TYPE;
        } catch (FileNotFoundException invalid) {
            return null;
        }
    }

    @Override public Cursor query(Uri uri, String[] projection, String selection,
                                  String[] selectionArgs, String sortOrder) {
        try {
            requireApkUri(uri);
            File file = apkFile();
            String[] columns = projection == null
                    ? new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE}
                    : projection;
            MatrixCursor cursor = new MatrixCursor(columns, 1);
            Object[] row = new Object[columns.length];
            String engine = BuildConfig.NATIVE_ENGINE ? "native" : "wasm";
            String scope = BuildConfig.ROM_LIBRARY ? "phase2" : "player";
            String name = getContext().getApplicationInfo().loadLabel(
                    getContext().getPackageManager()).toString().replaceAll("[^A-Za-z0-9._ -]", "_")
                    + "-" + engine + "-" + scope + ".apk";
            for (int i = 0; i < columns.length; i++) {
                if (OpenableColumns.DISPLAY_NAME.equals(columns[i])) row[i] = name;
                else if (OpenableColumns.SIZE.equals(columns[i])) row[i] = file.length();
            }
            cursor.addRow(row);
            return cursor;
        } catch (FileNotFoundException invalid) {
            return null;
        }
    }

    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        requireApkUri(uri);
        if (!"r".equals(mode)) throw new FileNotFoundException("APK share is read-only");
        return ParcelFileDescriptor.open(apkFile(), ParcelFileDescriptor.MODE_READ_ONLY);
    }

    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException("Read-only"); }
    @Override public int delete(Uri uri, String selection, String[] selectionArgs) { throw new UnsupportedOperationException("Read-only"); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) { throw new UnsupportedOperationException("Read-only"); }
}
