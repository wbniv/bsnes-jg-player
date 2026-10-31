# Vendored Android build dependency

- `zxing-core-3.5.4.jar` is `com.google.zxing:core:3.5.4`, downloaded from Maven Central.
- SHA-256: `71de5d89341b5fcf5dd89da7f44e84d825d0e084cdf3ec77c9abe26b0f0ceb13`.
- ZXing upstream: <https://github.com/zxing/zxing/tree/zxing-3.5.4>.
- License: Apache-2.0; the upstream license text is included as `ZXing-LICENSE.txt`.

The Android build container deliberately runs without network access. The pinned JAR is kept here so QR generation remains reproducible and offline.
