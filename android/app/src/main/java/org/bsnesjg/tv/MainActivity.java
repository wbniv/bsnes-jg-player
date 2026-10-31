package org.bsnesjg.tv;

import android.annotation.SuppressLint;
import android.app.AlertDialog;
import android.app.Activity;
import android.graphics.Color;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.ConsoleMessage;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.content.ClipData;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.widget.FrameLayout;
import android.opengl.GLSurfaceView;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView.Renderer;
import android.widget.TextView;
import android.os.SystemClock;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.IntBuffer;
import java.util.ArrayList;
import java.util.Collections;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Locale;
import com.google.zxing.WriterException;

public class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String START_URL = "https://" + HOST + "/assets/index.html";
    private long metricOriginNs;
    private WebView webView;
    private NativeRenderer nativeRenderer;
    // Keep the active ROM outside the GL renderer so a lost EGL surface can
    // recreate both the texture and the core's coroutine state on GLThread.
    private volatile byte[] activeRomBytes;
    private volatile String activeRomSlug = "";
    private GLSurfaceView glView;
    private volatile boolean paused = false;
    private volatile boolean cancelVerification = false;
    private Bitmap referenceFrame;
    private volatile String currentRom = "";
    private ApkTransferServer apkTransferServer;
    private AlertDialog apkTransferDialog;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        android.util.Log.i("BJG_TV_METRIC", "{\"event\":\"app_start\",\"app_version\":\"" + BuildConfig.VERSION_NAME + "\",\"version_code\":" + BuildConfig.VERSION_CODE + "}");
        // Android TV uses its D-pad directly; it never renders the optional
        // phone-controller overlay. Keep this explicit for device diagnostics.
        android.util.Log.i("BJG_TV_METRIC", "phone controller: off (Android TV remote input)");
        metricOriginNs = SystemClock.elapsedRealtimeNanos();
        // Emulation is active foreground media. Keep Android's screensaver and
        // display timeout from covering the game during long play/profile runs.
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(8, 12, 18));
        if (BuildConfig.NATIVE_ENGINE) createNativeSurface(root);

        webView = new WebView(this);
        webView.setBackgroundColor(BuildConfig.NATIVE_ENGINE ? Color.TRANSPARENT : Color.BLACK);
        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        // WebView throws SecurityException when network loads are enabled
        // without INTERNET permission. Packaged assets are served by the local
        // HTTPS interceptor below while external origins remain blocked.
        settings.setBlockNetworkLoads(true);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setSupportMultipleWindows(false);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        webView.addJavascriptInterface(new TvBridge(), "BjgAndroid");
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage message) {
                String line = message.message();
                if (line != null && line.startsWith("BJG_TV_METRIC ") && line.length() <= 4096) {
                    android.util.Log.i("BJG_TV_METRIC", line.substring("BJG_TV_METRIC ".length()));
                    return true;
                }
                android.util.Log.println(message.messageLevel() == ConsoleMessage.MessageLevel.ERROR
                                ? android.util.Log.ERROR : android.util.Log.INFO,
                        "BJG_WEBVIEW", message.message() + " (" + message.sourceId() + ":" + message.lineNumber() + ")");
                return super.onConsoleMessage(message);
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost())) {
                    android.util.Log.w("BJG_WEBVIEW", "blocked origin " + uri.getScheme() + "://" + uri.getHost());
                    return blocked();
                }
                String path = uri.getPath();
                if (path == null || !path.startsWith("/assets/")) {
                    android.util.Log.w("BJG_WEBVIEW", "blocked path " + path);
                    return blocked();
                }
                String asset = path.substring("/assets/".length());
                if (asset.isEmpty() || asset.contains("..") || asset.startsWith("/")) {
                    android.util.Log.w("BJG_WEBVIEW", "blocked asset " + asset);
                    return blocked();
                }
                try {
                    return new WebResourceResponse(mimeType(asset), null, getAssets().open(asset));
                } catch (IOException missing) {
                    android.util.Log.e("BJG_WEBVIEW", "missing local asset " + asset, missing);
                    return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", null,
                            new ByteArrayInputStream(new byte[0]));
                }
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                return !"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost());
            }
        });
        root.addView(webView, new FrameLayout.LayoutParams(-1, -1));
        setContentView(root);
        String directRom = getIntent().getStringExtra("rom");
        webView.loadUrl(START_URL + (BuildConfig.ROM_LIBRARY && directRom != null && directRom.matches("[a-z0-9-]{1,96}") ? "?rom=" + Uri.encode(directRom) : ""));
    }

    private void createNativeSurface(FrameLayout root) {
        if (BuildConfig.ROM_LIBRARY) {
            try {
                referenceFrame = BitmapFactory.decodeStream(getAssets().open("reference-5800.png"));
            } catch (IOException failure) { throw new IllegalStateException(failure); }
        }
        glView = new GLSurfaceView(this); glView.setEGLContextClientVersion(2);
        glView.setVisibility(View.GONE);
        nativeRenderer = new NativeRenderer(); glView.setRenderer(nativeRenderer);
        root.addView(glView, new FrameLayout.LayoutParams(-1, -1));
    }

    private final class NativeRenderer implements Renderer {
        private int texture, program, boundsLocation, frame = 0, w = 0, h = 0;
        private boolean referenceChecked = false;
        private boolean pixelSampleReported = false;
        private long lastRendererDiagnosticNs;
        private boolean surfaceCreated = false;
        private volatile boolean hasRom = false;
        private volatile String romSlug = "";
        private volatile float[] gameRect = {0f, 0f, 1f, 1f};
        private final ByteBuffer rgba = ByteBuffer.allocateDirect(256 * 224 * 4);
        private ByteBuffer verticesBuffer;
        private final float[] drawVertices = new float[8];
        private long lastNs; private double credit;
        private long sampleStartNs;
        private long lastCallbackNs;
        private int sampleSteps, sampleDraws;
        private double peakCredit;
        private final ArrayList<Double> coreSamplesMs = new ArrayList<>();
        private final ArrayList<Double> drawSamplesMs = new ArrayList<>();
        private final ArrayList<Double> callbackIntervalsMs = new ArrayList<>();
        @Override public void onSurfaceCreated(GL10 gl, EGLConfig config) {
            GLES20.glClearColor(0,0,0,1); initGl();
            boolean recreated = surfaceCreated;
            surfaceCreated = true;
            android.util.Log.i("BJG_TV_METRIC", "{\"event\":\"renderer_surface\",\"app_version\":\"" + BuildConfig.VERSION_NAME + "\",\"recreated\":" + recreated + ",\"gl_version\":\"" + GLES20.glGetString(GLES20.GL_VERSION) + "\",\"gl_vendor\":\"" + GLES20.glGetString(GLES20.GL_VENDOR) + "\",\"gl_renderer\":\"" + GLES20.glGetString(GLES20.GL_RENDERER) + "\"}");
            byte[] rom = activeRomBytes;
            String slug = activeRomSlug;
            if (recreated && hasRom && rom != null && !slug.isEmpty()) {
                // GLSurfaceView can recreate its EGL context after the app is
                // backgrounded or the display changes. Rebuild the emulator
                // on this GL thread too; its libco coroutines belong to the
                // thread that powered the core.
                boolean restored = NativeEngine.load(getAssets(), rom, slug + ".sfc");
                setRom(restored ? slug : "", restored);
                android.util.Log.i("BJG_NATIVE", "surface_recreated rom=" + slug + " restored=" + restored);
            }
        }
        private void initGl() {
            int[] t=new int[1]; GLES20.glGenTextures(1,t,0); texture=t[0]; GLES20.glBindTexture(GLES20.GL_TEXTURE_2D,texture);
            GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D,GLES20.GL_TEXTURE_MIN_FILTER,GLES20.GL_NEAREST);
            GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D,GLES20.GL_TEXTURE_MAG_FILTER,GLES20.GL_NEAREST);
            String vs="attribute vec2 p; varying vec2 uv; uniform vec4 bounds; void main(){gl_Position=vec4(p,0.,1.);uv=(p-bounds.xy)/bounds.zw;}";
            String fs="precision mediump float; varying vec2 uv; uniform sampler2D tex; void main(){gl_FragColor=texture2D(tex,vec2(uv.x,1.-uv.y));}";
            int v=shader(GLES20.GL_VERTEX_SHADER,vs),f=shader(GLES20.GL_FRAGMENT_SHADER,fs);program=GLES20.glCreateProgram();GLES20.glAttachShader(program,v);GLES20.glAttachShader(program,f);GLES20.glLinkProgram(program);int[] status=new int[1];GLES20.glGetProgramiv(program,GLES20.GL_LINK_STATUS,status,0);boundsLocation=GLES20.glGetUniformLocation(program,"bounds");if(status[0]==0)android.util.Log.e("BJG_TV_METRIC","{\"event\":\"renderer_program_link_failed\",\"log\":\""+GLES20.glGetProgramInfoLog(program).replace("\\","\\\\").replace("\"","\\\"").replace("\n"," ")+"\"}");
        }
        private int shader(int type,String src){int s=GLES20.glCreateShader(type);GLES20.glShaderSource(s,src);GLES20.glCompileShader(s);int[] status=new int[1];GLES20.glGetShaderiv(s,GLES20.GL_COMPILE_STATUS,status,0);if(status[0]==0)android.util.Log.e("BJG_TV_METRIC","{\"event\":\"renderer_shader_compile_failed\",\"type\":"+type+",\"log\":\""+GLES20.glGetShaderInfoLog(s).replace("\\","\\\\").replace("\"","\\\"").replace("\n"," ")+"\"}");return s;}
        void resetPerformanceWindow() { sampleStartNs=0;lastCallbackNs=0;sampleSteps=0;sampleDraws=0;peakCredit=0;coreSamplesMs.clear();drawSamplesMs.clear();callbackIntervalsMs.clear(); }
        void setRom(String slug, boolean loaded) { frame=0;credit=0;lastNs=0;referenceChecked=false;pixelSampleReported=false;romSlug=slug;hasRom=loaded;paused=false;resetPerformanceWindow(); }
        void pauseGame() { paused=true; }
        void resumeGame() { paused=false; }
        void restartGame() { NativeEngine.reset();frame=0;credit=0;lastNs=0;referenceChecked=false;paused=false;resetPerformanceWindow(); }
        void renderVerification(int callbackId) {
            paused=true;
            boolean mandelCheck = "mandel-display".equals(romSlug);
            boolean playerCheck = BuildConfig.PLAYER_ROM_SLUG.equals(romSlug) && !"{}".equals(BuildConfig.PLAYER_ROM_SELFCHECK);
            if (!mandelCheck && !playerCheck) { finishVerification(callbackId, false); return; }
            int frames, offset, expectedValue;
            try {
                if (mandelCheck) {
                    frames = 5800; offset = 0x580; expectedValue = 0x204F;
                } else {
                    org.json.JSONObject spec = new org.json.JSONObject(BuildConfig.PLAYER_ROM_SELFCHECK);
                    frames = spec.getInt("frames");
                    offset = Integer.decode(spec.getString("offset"));
                    expectedValue = Integer.decode(spec.getString("want"));
                }
            } catch (org.json.JSONException invalidConfig) {
                android.util.Log.e("BJG_TV_METRIC", "Invalid configured player ROM self-check", invalidConfig);
                finishVerification(callbackId, false); return;
            }
            cancelVerification=false;NativeEngine.reset();
            for (int i=0;i<frames&&!cancelVerification;i++) NativeEngine.step();
            if(cancelVerification){finishVerification(callbackId,"cancelled");paused=false;return;}
            int got=NativeEngine.wramWord(offset);boolean pass=got==expectedValue;
            int diff=-1;
            if(mandelCheck&&referenceFrame!=null){int width=NativeEngine.width(),height=NativeEngine.height();ByteBuffer checkPixels=ByteBuffer.allocateDirect(256*224*4);NativeEngine.copyPixels(checkPixels);int[] expected=new int[width*height];referenceFrame.getPixels(expected,0,width,0,0,width,height);diff=0;for(int i=0;i<expected.length;i++){int p=i*4,e=expected[i];if(checkPixels.get(p)!=(byte)((e>>16)&255)||checkPixels.get(p+1)!=(byte)((e>>8)&255)||checkPixels.get(p+2)!=(byte)(e&255))diff++;}pass=pass&&diff==0;}
            android.util.Log.i("BJG_TV_METRIC","{\"engine\":\"native\",\"phase\":\"verification\",\"rom\":\""+romSlug+"\",\"frame\":"+frames+",\"wram\":"+got+",\"differentPixels\":"+diff+",\"status\":\""+(pass?"pass":"fail")+"\"}");
            finishVerification(callbackId,pass);paused=false;
        }
        private void finishVerification(int callbackId, Object pass) {
            runOnUiThread(() -> { if(webView!=null)webView.evaluateJavascript("window.__bjgNativeResolve("+callbackId+","+ (pass instanceof String ? "'"+pass+"'" : pass) +")",null); });
        }
        @Override public void onSurfaceChanged(GL10 gl,int width,int height){GLES20.glViewport(0,0,width,height); if(program==0)initGl();}
        void setGameRect(float left,float top,float width,float height) {
            gameRect=new float[]{left,top,width,height};
        }
        private double mean(ArrayList<Double> values) {
            if(values.isEmpty())return 0;double sum=0;for(double value:values)sum+=value;return sum/values.size();
        }
        private double p95(ArrayList<Double> values) {
            if(values.isEmpty())return 0;ArrayList<Double> sorted=new ArrayList<>(values);Collections.sort(sorted);return sorted.get(Math.max(0,(int)Math.ceil(sorted.size()*.95)-1));
        }
        private double max(ArrayList<Double> values) {
            double result=0;for(double value:values)result=Math.max(result,value);return result;
        }
        private void publishPerformance(long now) {
            long elapsed=now-sampleStartNs;if(elapsed<1_000_000_000L)return;
            double emuFps=sampleSteps*1_000_000_000.0/elapsed,drawFps=sampleDraws*1_000_000_000.0/elapsed;
            double coreMean=mean(coreSamplesMs),coreP95=p95(coreSamplesMs),coreMax=max(coreSamplesMs),drawMean=mean(drawSamplesMs),drawP95=p95(drawSamplesMs),callbackP95=p95(callbackIntervalsMs);
            String payload=String.format(Locale.US,"{\"emuFps\":%.2f,\"drawFps\":%.2f,\"coreMeanMs\":%.3f,\"coreP95Ms\":%.3f,\"drawMeanMs\":%.3f,\"drawP95Ms\":%.3f,\"backlogFrames\":%.2f,\"windowMs\":%.1f}",emuFps,drawFps,coreMean,coreP95,drawMean,drawP95,credit,elapsed/1_000_000.0);
            android.util.Log.i("BJG_TV_METRIC",String.format(Locale.US,"{\"event\":\"playback_window\",\"engine\":\"native\",\"rom\":\"%s\",\"t_ms\":%d,\"rom_run\":1,\"frames\":%d,\"rom_frames\":%d,\"sample_frames\":%d,\"window_ms\":%.1f,\"target_hz\":60.0988,\"core_mean_ms\":%.3f,\"core_p95_ms\":%.3f,\"core_max_ms\":%.3f,\"canvas_callbacks\":%d,\"canvas_submit_mean_ms\":%.3f,\"canvas_submit_p95_ms\":%.3f,\"surface_callback_p95_ms\":%.3f,\"raf_interval_p95_ms\":%.3f,\"emulation_backlog_frames\":%.2f,\"peak_backlog_frames\":%.2f,\"emu_fps\":%.2f,\"draw_fps\":%.2f}",romSlug,Math.max(0,(now-metricOriginNs)/1_000_000L),frame,frame,sampleSteps,elapsed/1_000_000.0,coreMean,coreP95,coreMax,sampleDraws,drawMean,drawP95,callbackP95,callbackP95,credit,peakCredit,emuFps,drawFps));
            runOnUiThread(()->{if(webView!=null)webView.evaluateJavascript("window.BJGPerformance&&window.BJGPerformance.publish("+payload+")",null);});
            sampleStartNs=now;sampleSteps=0;sampleDraws=0;peakCredit=0;coreSamplesMs.clear();drawSamplesMs.clear();callbackIntervalsMs.clear();
        }
        private void checkReferenceFrame() {
            if (referenceChecked || referenceFrame == null) return;
            referenceChecked = true;
            int width = NativeEngine.width(), height = NativeEngine.height();
            NativeEngine.copyPixels(rgba);
            int[] expected = new int[width * height];
            referenceFrame.getPixels(expected, 0, width, 0, 0, width, height);
            int diff = 0;
            for (int i = 0; i < expected.length; i++) {
                int p = i * 4, e = expected[i];
                if (rgba.get(p) != (byte) (e >> 16) || rgba.get(p + 1) != (byte) (e >> 8)
                        || rgba.get(p + 2) != (byte) e) diff++;
            }
            android.util.Log.i("BJG_TV_METRIC", "{\"engine\":\"native\",\"phase\":\"framebuffer\",\"frame\":5800,\"differentPixels\":"
                    + diff + ",\"pixels\":" + (width * height) + ",\"status\":\"" + (diff == 0 ? "pass" : "fail") + "\"}");
        }
        @Override public void onDrawFrame(GL10 gl){
            if(!hasRom){GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT);return;}
            long now=SystemClock.elapsedRealtimeNanos();if(sampleStartNs==0)sampleStartNs=now;if(lastCallbackNs>0)callbackIntervalsMs.add((now-lastCallbackNs)/1_000_000.0);lastCallbackNs=now;if(lastNs==0)lastNs=now;credit+=Math.min(.25,(now-lastNs)/1e9)*60.0988;lastNs=now;peakCredit=Math.max(peakCredit,credit);
            if(!paused){int steps=Math.min(4,(int)credit);for(int i=0;i<steps;i++){long coreStart=SystemClock.elapsedRealtimeNanos();NativeEngine.step();long coreEnd=SystemClock.elapsedRealtimeNanos();coreSamplesMs.add((coreEnd-coreStart)/1_000_000.0);sampleSteps++;frame++;credit-=1;if(frame==5800&&"mandel-display".equals(romSlug)){checkReferenceFrame();int got=NativeEngine.wramWord(0x580);android.util.Log.i("BJG_TV_METRIC","{\"engine\":\"native\",\"phase\":\"correctness\",\"frame\":5800,\"offset\":1408,\"expected\":8271,\"actual\":"+got+",\"status\":\""+(got==0x204f?"pass":"fail")+"\"}");if(getIntent().getBooleanExtra("layoutProof",false)){paused=true;break;}}}}
            w=NativeEngine.width();h=NativeEngine.height();if(w<=0||h<=0)return;long drawStart=SystemClock.elapsedRealtimeNanos();NativeEngine.copyPixels(rgba);rgba.position(0);if(!pixelSampleReported&&frame>=30){int lit=0,samples=0;for(int y=0;y<h;y+=8)for(int x=0;x<w;x+=8){int p=(y*w+x)*4;samples++;if(((rgba.get(p)&255)|(rgba.get(p+1)&255)|(rgba.get(p+2)&255))!=0)lit++;}android.util.Log.i("BJG_TV_METRIC","{\"event\":\"native_rgba_sample\",\"rom\":\""+romSlug+"\",\"frame\":"+frame+",\"width\":"+w+",\"height\":"+h+",\"lit_samples\":"+lit+",\"samples\":"+samples+"}");pixelSampleReported=true;}
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT);GLES20.glUseProgram(program);GLES20.glBindTexture(GLES20.GL_TEXTURE_2D,texture);
            float[] rect=gameRect;
            float left=-1f+2f*rect[0],right=-1f+2f*(rect[0]+rect[2]);
            float top=1f-2f*rect[1],bottom=1f-2f*(rect[1]+rect[3]);
            GLES20.glUniform4f(boundsLocation,left,bottom,right-left,top-bottom);
            drawVertices[0]=left;drawVertices[1]=bottom;drawVertices[2]=right;drawVertices[3]=bottom;
            drawVertices[4]=left;drawVertices[5]=top;drawVertices[6]=right;drawVertices[7]=top;
            if(verticesBuffer==null)verticesBuffer=ByteBuffer.allocateDirect(32).order(ByteOrder.nativeOrder());
            verticesBuffer.position(0);for(float vertex:drawVertices)verticesBuffer.putFloat(vertex);verticesBuffer.position(0);
            int loc=GLES20.glGetAttribLocation(program,"p");GLES20.glEnableVertexAttribArray(loc);GLES20.glVertexAttribPointer(loc,2,GLES20.GL_FLOAT,false,0,verticesBuffer);
            GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D,0,GLES20.GL_RGBA,w,h,0,GLES20.GL_RGBA,GLES20.GL_UNSIGNED_BYTE,rgba);GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP,0,4);
            long drawEnd=SystemClock.elapsedRealtimeNanos();drawSamplesMs.add((drawEnd-drawStart)/1_000_000.0);sampleDraws++;if(drawEnd-lastRendererDiagnosticNs>=5_000_000_000L){int lit=0,samples=0;for(int y=0;y<h;y+=8)for(int x=0;x<w;x+=8){int p=(y*w+x)*4;samples++;if(((rgba.get(p)&255)|(rgba.get(p+1)&255)|(rgba.get(p+2)&255))!=0)lit++;}int glError=GLES20.glGetError();android.util.Log.i("BJG_TV_METRIC",String.format(Locale.US,"{\"event\":\"renderer_health\",\"app_version\":\"%s\",\"rom\":\"%s\",\"frame\":%d,\"width\":%d,\"height\":%d,\"lit_samples\":%d,\"samples\":%d,\"game_rect\":[%.4f,%.4f,%.4f,%.4f],\"program\":%d,\"bounds_location\":%d,\"gl_error\":%d}",BuildConfig.VERSION_NAME,romSlug,frame,w,h,lit,samples,rect[0],rect[1],rect[2],rect[3],program,boundsLocation,glError));lastRendererDiagnosticNs=drawEnd;}publishPerformance(drawEnd);
        }
    }

    private static WebResourceResponse blocked() {
        return new WebResourceResponse("text/plain", "UTF-8", 403, "Forbidden", null,
                new ByteArrayInputStream(new byte[0]));
    }

    private static String mimeType(String name) {
        String lower = name.toLowerCase(Locale.ROOT);
        if (lower.endsWith(".html")) return "text/html";
        if (lower.endsWith(".css")) return "text/css";
        if (lower.endsWith(".js")) return "application/javascript";
        if (lower.endsWith(".json")) return "application/json";
        if (lower.endsWith(".wasm")) return "application/wasm";
        if (lower.endsWith(".sfc")) return "application/octet-stream";
        return "application/octet-stream";
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (!BuildConfig.NATIVE_ENGINE && event.getAction() == KeyEvent.ACTION_DOWN && event.getKeyCode() == KeyEvent.KEYCODE_F9) {
            if (webView != null) webView.evaluateJavascript("window.BJGTV&&window.BJGTV.benchmark(600)", null);
            return true;
        }
        if (event.getAction() == KeyEvent.ACTION_DOWN && event.getKeyCode() == KeyEvent.KEYCODE_BACK) {
            if (webView != null) webView.evaluateJavascript("window.bjgTvBack && window.bjgTvBack()", null);
            return true;
        }
        if (event.getKeyCode() == KeyEvent.KEYCODE_BACK) return true;
        if (isRemoteNavigation(event.getKeyCode())) {
            return super.dispatchKeyEvent(event);
        }
        return super.dispatchKeyEvent(event);
    }

    private static boolean isRemoteNavigation(int keyCode) {
        return keyCode == KeyEvent.KEYCODE_DPAD_UP || keyCode == KeyEvent.KEYCODE_DPAD_DOWN ||
                keyCode == KeyEvent.KEYCODE_DPAD_LEFT || keyCode == KeyEvent.KEYCODE_DPAD_RIGHT ||
                keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER ||
                keyCode == KeyEvent.KEYCODE_NUMPAD_ENTER;
    }

    @Override
    protected void onPause() {
        if (BuildConfig.NATIVE_ENGINE && glView != null) { paused = true; glView.onPause(); }
        if (webView != null) {
            webView.evaluateJavascript("window.BJGTV && window.BJGTV.background()", null);
            webView.onPause();
        }
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (BuildConfig.NATIVE_ENGINE && glView != null) glView.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (BuildConfig.NATIVE_ENGINE && glView != null) glView.onPause();
        if (webView != null) {
            webView.removeJavascriptInterface("BjgAndroid");
            webView.destroy();
            webView = null;
        }
        stopApkTransfer();
        super.onDestroy();
    }

    private void showLocalApkTransfer() {
        stopApkTransfer();
        try {
            apkTransferServer = ApkTransferServer.start(new File(getApplicationInfo().sourceDir));
            apkTransferDialog = ApkTransferDialog.create(MainActivity.this, apkTransferServer);
            apkTransferDialog.show();
        } catch (IOException | WriterException failure) {
            stopApkTransfer();
            android.widget.Toast.makeText(MainActivity.this,
                    failure.getMessage() == null ? "Could not start APK transfer" : failure.getMessage(),
                    android.widget.Toast.LENGTH_LONG).show();
            android.util.Log.w("BJG_APK_SHARE", "Could not start local APK transfer", failure);
            if (!BuildConfig.PUBLIC_DOWNLOAD_URL.isEmpty()) showPublicDownloadQr();
        }
    }

    private void stopApkTransfer() {
        if (apkTransferDialog != null) {
            apkTransferDialog.setOnDismissListener(null);
            apkTransferDialog.dismiss();
            apkTransferDialog = null;
        }
        if (apkTransferServer != null) {
            apkTransferServer.close();
            apkTransferServer = null;
        }
    }

    private void showApkShareOptions() {
        CharSequence[] options = BuildConfig.PUBLIC_DOWNLOAD_URL.isEmpty()
                ? new CharSequence[]{"Share with another app", "Local transfer QR"}
                : new CharSequence[]{"Share with another app", "Local transfer QR", "Public download QR"};
        new AlertDialog.Builder(MainActivity.this)
                .setTitle(BuildConfig.ROM_LIBRARY ? "Share app APK and ROM library" : "Share app APK")
                .setItems(options, (dialog, choice) -> {
                    if (choice == 0) shareApkWithAndroid();
                    else if (choice == 1) showLocalApkTransfer();
                    else showPublicDownloadQr();
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void showPublicDownloadQr() {
        try {
            AlertDialog dialog = ApkTransferDialog.createForUrl(
                    MainActivity.this,
                    BuildConfig.PUBLIC_DOWNLOAD_URL,
                    "Scan this code to open the public release page and choose an APK. " +
                            "The published version may differ from this installed app. " +
                            "The recipient needs internet access; this device does not upload the APK.",
                    "Public APK download");
            dialog.show();
        } catch (WriterException failure) {
            android.widget.Toast.makeText(MainActivity.this,
                    "Could not create the public download QR code", android.widget.Toast.LENGTH_LONG).show();
            android.util.Log.w("BJG_APK_SHARE", "Could not create public download QR", failure);
        }
    }

    private void shareApkWithAndroid() {
        try {
            Uri apk = new Uri.Builder()
                    .scheme("content")
                    .authority(getPackageName() + ".apkshare")
                    .appendPath("app.apk")
                    .build();
            Intent send = new Intent(Intent.ACTION_SEND)
                    .setType("application/vnd.android.package-archive")
                    .putExtra(Intent.EXTRA_STREAM, apk)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            send.setClipData(ClipData.newUri(getContentResolver(), "App APK", apk));
            startActivity(Intent.createChooser(send, "Share app APK"));
        } catch (RuntimeException unavailable) {
            android.util.Log.w("BJG_APK_SHARE", "Sharesheet unavailable; offering local transfer", unavailable);
            showLocalApkTransfer();
        }
    }

    private final class TvBridge {
        @JavascriptInterface
        public String getAppVersion() { return BuildConfig.VERSION_NAME; }

        @JavascriptInterface
        public String getPlayerRomSlug() { return BuildConfig.PLAYER_ROM_SLUG; }

        @JavascriptInterface
        public String getPlayerRomTitle() { return BuildConfig.PLAYER_ROM_TITLE; }

        @JavascriptInterface
        public boolean hasPlayerRomSelfCheck() { return !"{}".equals(BuildConfig.PLAYER_ROM_SELFCHECK); }

        @JavascriptInterface
        public void setGameRect(double left, double top, double width, double height) {
            if (!BuildConfig.NATIVE_ENGINE || glView == null || !Double.isFinite(left)
                    || !Double.isFinite(top) || !Double.isFinite(width) || !Double.isFinite(height)
                    || left < 0 || top < 0 || width <= 0 || height <= 0
                    || left + width > 1.0001 || top + height > 1.0001) return;
            float boundedWidth = (float) Math.min(width, 1 - left);
            float boundedHeight = (float) Math.min(height, 1 - top);
            nativeRenderer.setGameRect((float) left, (float) top, boundedWidth, boundedHeight);
        }

        @JavascriptInterface
        public boolean getPerformanceOverlayEnabled() {
            return getSharedPreferences("tv-performance", MODE_PRIVATE).getBoolean("enabled", true);
        }

        @JavascriptInterface
        public boolean setPerformanceOverlayEnabled(boolean enabled) {
            return getSharedPreferences("tv-performance", MODE_PRIVATE).edit().putBoolean("enabled", enabled).commit();
        }

        @JavascriptInterface
        public String getPrefs() {
            return getSharedPreferences("rom-library", MODE_PRIVATE).getString("state", "{}");
        }

        @JavascriptInterface
        public boolean setPrefs(String json) {
            if (!BuildConfig.ROM_LIBRARY || json == null || json.length() > 65536) return false;
            try {
                org.json.JSONObject state = new org.json.JSONObject(json);
                org.json.JSONArray favorites = state.optJSONArray("favorites");
                if (favorites == null) return false;
                for (int i = 0; i < favorites.length(); i++) {
                    String slug = favorites.optString(i, "");
                    if (!slug.matches("[a-z0-9-]{1,96}")) return false;
                }
                String lastPlayed = state.optString("lastPlayed", "");
                if (!lastPlayed.isEmpty() && !lastPlayed.matches("[a-z0-9-]{1,96}")) return false;
                return getSharedPreferences("rom-library", MODE_PRIVATE).edit().putString("state", state.toString()).commit();
            } catch (org.json.JSONException invalid) { return false; }
        }

        @JavascriptInterface
        public void exitApp() {
            if (getIntent().getBooleanExtra("benchmark", false)) {
                android.util.Log.w("BJG_TV_METRIC", "{\"event\":\"benchmark_exit_ignored\"}");
                return;
            }
            runOnUiThread(MainActivity.this::finish);
        }

        @JavascriptInterface
        public void shareApk() {
            if (getIntent().getBooleanExtra("benchmark", false)) return;
            runOnUiThread(() -> {
                if (getPackageManager().hasSystemFeature(PackageManager.FEATURE_LEANBACK)) {
                    if (BuildConfig.PUBLIC_DOWNLOAD_URL.isEmpty()) {
                        showLocalApkTransfer();
                    } else {
                        new AlertDialog.Builder(MainActivity.this)
                                .setTitle("Share app APK")
                                .setItems(new CharSequence[]{"Local transfer QR", "Public download QR"},
                                        (dialog, choice) -> {
                                            if (choice == 0) showLocalApkTransfer();
                                            else showPublicDownloadQr();
                                        })
                                .setNegativeButton("Cancel", null)
                                .show();
                    }
                    return;
                }
                showApkShareOptions();
            });
        }

        @JavascriptInterface
        public void playRom(String slug, int callbackId) {
            if (!BuildConfig.NATIVE_ENGINE || slug == null || !slug.matches("[a-z0-9-]{1,96}")) { resolve(callbackId, false); return; }
            paused = true;
            new Thread(() -> {
                byte[] rom;
                try { rom = NativeEngine.read(getAssets().open("roms/" + slug + ".sfc")); }
                catch (IOException failure) { android.util.Log.e("BJG_NATIVE", "ROM asset missing: " + slug, failure); resolve(callbackId, false); return; }
                activeRomBytes = rom;
                activeRomSlug = slug;
                runOnUiThread(() -> { if (glView != null) glView.setVisibility(View.VISIBLE); });
                if (glView != null) glView.queueEvent(() -> {
                    boolean ok = NativeEngine.load(getAssets(), rom, slug + ".sfc");
                    currentRom = ok ? slug : "";
                    nativeRenderer.setRom(currentRom, ok);
                    long loadedAt=SystemClock.elapsedRealtimeNanos();
                    android.util.Log.i("BJG_TV_METRIC","{\"event\":\"core_ready\",\"engine\":\"native\",\"core\":\"bsnes-jg\",\"version\":\"2.1.0\",\"t_ms\":"+Math.max(0,(loadedAt-metricOriginNs)/1_000_000L)+"}");
                    android.util.Log.i("BJG_TV_METRIC","{\"event\":\"rom_loaded\",\"engine\":\"native\",\"rom\":\""+slug+"\",\"t_ms\":"+Math.max(0,(loadedAt-metricOriginNs)/1_000_000L)+",\"ok\":"+ok+"}");
                    runOnUiThread(() -> resolve(callbackId, ok));
                });
            }, "bjg-rom-loader").start();
        }

        @JavascriptInterface public void pauseGame() { paused = true; }
        @JavascriptInterface public void resumeGame() {
            if (glView != null) runOnUiThread(() -> glView.setVisibility(View.VISIBLE));
            paused = false;
        }
        @JavascriptInterface public void showLibrary() {
            paused = true;
            if (glView != null) runOnUiThread(() -> glView.setVisibility(View.GONE));
        }
        @JavascriptInterface public void restartGame(int callbackId) {
            if (glView == null || currentRom.isEmpty()) { resolve(callbackId, false); return; }
            glView.queueEvent(() -> { nativeRenderer.restartGame(); resolve(callbackId, true); });
        }
        @JavascriptInterface public void verifyGame(int callbackId) {
            boolean configuredCheck = BuildConfig.PLAYER_ROM_SLUG.equals(currentRom) && !"{}".equals(BuildConfig.PLAYER_ROM_SELFCHECK);
            if (glView == null || (!"mandel-display".equals(currentRom) && !configuredCheck)) { resolve(callbackId, false); return; }
            glView.queueEvent(() -> nativeRenderer.renderVerification(callbackId));
        }
        @JavascriptInterface public void cancelVerify() { cancelVerification = true; }
        private void resolve(int callbackId, boolean result) {
            runOnUiThread(() -> { if (webView != null) webView.evaluateJavascript("window.__bjgNativeResolve(" + callbackId + "," + result + ")", null); });
        }
    }
}
