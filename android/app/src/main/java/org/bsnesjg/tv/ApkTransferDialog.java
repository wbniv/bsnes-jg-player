package org.bsnesjg.tv;

import android.app.AlertDialog;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.google.zxing.BarcodeFormat;
import com.google.zxing.EncodeHintType;
import com.google.zxing.WriterException;
import com.google.zxing.qrcode.QRCodeWriter;
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel;

import java.util.EnumMap;
import java.util.Map;

final class ApkTransferDialog {
    private ApkTransferDialog() {}

    static AlertDialog create(Context context, ApkTransferServer server) throws WriterException {
        return createForUrl(context, server.url(),
                "Connect the phone to the same Wi-Fi, scan this code, then tap Download APK. " +
                        "The private link expires in 10 minutes and allows up to 5 downloads.",
                "Share app APK", server);
    }

    static AlertDialog createForUrl(Context context, String url, String instructions, String title)
            throws WriterException {
        return createForUrl(context, url, instructions, title, null);
    }

    private static AlertDialog createForUrl(Context context, String url, String instructionText,
                                           String title, ApkTransferServer server) throws WriterException {
        int edge = dp(context, 320);
        Bitmap qr = makeQr(url, edge);

        LinearLayout content = new LinearLayout(context);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(context, 20), dp(context, 8), dp(context, 20), dp(context, 8));

        ImageView image = new ImageView(context);
        image.setImageBitmap(qr);
        image.setScaleType(ImageView.ScaleType.FIT_CENTER);
        image.setContentDescription("Scan this QR code on the receiving Android phone to download the APK");
        content.addView(image, new LinearLayout.LayoutParams(edge, edge));

        TextView instructions = new TextView(context);
        instructions.setText(instructionText);
        instructions.setTextColor(Color.WHITE);
        instructions.setTextSize(18);
        instructions.setPadding(0, dp(context, 12), 0, dp(context, 12));
        content.addView(instructions, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView address = new TextView(context);
        address.setText(url);
        address.setTextColor(0xffa9c5da);
        address.setTextSize(12);
        address.setTextIsSelectable(true);
        content.addView(address, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        AlertDialog dialog = new AlertDialog.Builder(context)
                .setTitle(title)
                .setView(content)
                .setPositiveButton("Done", (ignored, which) -> {})
                .create();
        if (server != null) dialog.setOnDismissListener(ignored -> server.close());
        return dialog;
    }

    private static Bitmap makeQr(String value, int edge) throws WriterException {
        Map<EncodeHintType, Object> hints = new EnumMap<>(EncodeHintType.class);
        hints.put(EncodeHintType.ERROR_CORRECTION, ErrorCorrectionLevel.M);
        hints.put(EncodeHintType.MARGIN, 2);
        com.google.zxing.common.BitMatrix matrix = new QRCodeWriter().encode(
                value, BarcodeFormat.QR_CODE, edge, edge, hints);
        Bitmap bitmap = Bitmap.createBitmap(edge, edge, Bitmap.Config.RGB_565);
        for (int y = 0; y < edge; y++) {
            for (int x = 0; x < edge; x++) {
                bitmap.setPixel(x, y, matrix.get(x, y) ? Color.BLACK : Color.WHITE);
            }
        }
        return bitmap;
    }

    private static int dp(Context context, int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }
}
