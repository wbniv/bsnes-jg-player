# Keep Android's annotated JavaScript bridge entry point available to WebView.
-keepclassmembers class org.bsnesjg.tv.MainActivity$TvBridge {
    @android.webkit.JavascriptInterface <methods>;
}

# JNI entry names are resolved from native symbols at runtime.
-keepclasseswithmembernames,includedescriptorclasses class * {
    native <methods>;
}
