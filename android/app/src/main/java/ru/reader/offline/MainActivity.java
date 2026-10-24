package ru.reader.offline;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.util.Base64;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/**
 * WebView-обёртка над index.html (лежит в assets).
 * Ни одного разрешения в манифесте: у приложения нет INTERNET,
 * поэтому у него физически нет возможности отправить что-либо в сеть.
 */
public class MainActivity extends Activity {

    private static final int FILE_CHOOSER_REQUEST = 42;
    private static final long MAX_INTENT_BOOK = 128L * 1024 * 1024;

    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private Uri intentUri;
    private String intentPayload; // "имя|base64"

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Intent i = getIntent();
        if (i != null && i.getData() != null) intentUri = i.getData();

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        web.setBackgroundColor(0xFFF1E7D0);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView v, String url) {
                // на случай, если книга пришла через «Открыть с помощью»
                v.evaluateJavascript(
                    "if(window.__intentBook)window.__intentBook();", null);
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb,
                                             FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = cb;
                try {
                    startActivityForResult(params.createIntent(), FILE_CHOOSER_REQUEST);
                } catch (Exception e) {
                    fileCallback = null;
                    return false;
                }
                return true;
            }
        });

        web.addJavascriptInterface(new Bridge(), "Android");
        web.loadUrl("file:///android_asset/index.html");
        setContentView(web);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_REQUEST && fileCallback != null) {
            fileCallback.onReceiveValue(
                WebChromeClient.FileChooserParams.parseResult(resultCode, data));
            fileCallback = null;
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }

    @Override
    public void onBackPressed() {
        if (web == null) { super.onBackPressed(); return; }
        web.evaluateJavascript("(window.__r&&window.__r.isReading())?'1':'0'",
            new ValueCallback<String>() {
                @Override public void onReceiveValue(String v) {
                    if (v != null && v.contains("1")) {
                        web.evaluateJavascript("window.__r.backToLibrary()", null);
                    } else {
                        finish();
                    }
                }
            });
    }

    private String displayName(Uri uri) {
        Cursor c = null;
        try {
            c = getContentResolver().query(uri, null, null, null, null);
            if (c != null && c.moveToFirst()) {
                int idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (idx >= 0) {
                    String n = c.getString(idx);
                    if (n != null && !n.isEmpty()) return n;
                }
            }
        } catch (Exception ignored) {
        } finally {
            if (c != null) c.close();
        }
        String p = uri.getLastPathSegment();
        return p == null ? "книга.epub" : p;
    }

    private class Bridge {
        /** Экран не гаснет, пока открыта книга. */
        @JavascriptInterface
        public void keepScreenOn(final boolean on) {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    if (on) getWindow().addFlags(
                        WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    else getWindow().clearFlags(
                        WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                }
            });
        }

        /** Книга, пришедшая через «Открыть с помощью». Отдаётся один раз. */
        @JavascriptInterface
        public String intentBook() {
            if (intentUri == null) return "";
            if (intentPayload == null) {
                try {
                    InputStream in = getContentResolver().openInputStream(intentUri);
                    ByteArrayOutputStream out = new ByteArrayOutputStream();
                    byte[] buf = new byte[65536];
                    long total = 0;
                    int n;
                    while ((n = in.read(buf)) > 0) {
                        out.write(buf, 0, n);
                        total += n;
                        if (total > MAX_INTENT_BOOK) break;
                    }
                    in.close();
                    intentPayload = displayName(intentUri) + "|" +
                        Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP);
                } catch (Exception e) {
                    intentPayload = "";
                }
            }
            String r = intentPayload;
            intentUri = null;
            return r;
        }
    }
}
