package com.kebiao.app;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * 零依赖 WebView 壳：assets 里的课表 App 通过 shouldInterceptRequest 挂在
 * https://kebiao.local/ 下（真实 origin，localStorage 可用），无任何网络权限。
 */
public class MainActivity extends Activity {

    private static final String HOST = "kebiao.local";
    private static final int REQ_FILE = 41, REQ_SAVE = 42;

    private WebView web;
    private ValueCallback<Uri[]> fileCb;
    private String saveName, saveMime, saveText;

    private static final Map<String, String> MIME = new HashMap<>();
    static {
        MIME.put("html", "text/html");
        MIME.put("js", "application/javascript");
        MIME.put("css", "text/css");
        MIME.put("json", "application/json");
        MIME.put("png", "image/png");
        MIME.put("jpg", "image/jpeg");
        MIME.put("jpeg", "image/jpeg");
        MIME.put("gif", "image/gif");
        MIME.put("svg", "image/svg+xml");
        MIME.put("ico", "image/x-icon");
        MIME.put("txt", "text/plain");
        MIME.put("woff2", "font/woff2");
    }
    private static String mime(String name) {
        int i = name.lastIndexOf('.');
        String m = MIME.get(i < 0 ? "" : name.substring(i + 1).toLowerCase());
        return m == null ? "application/octet-stream" : m;
    }

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        setContentView(R.layout.activity_main);
        web = findViewById(R.id.web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        web.setWebViewClient(new Local());
        web.setWebChromeClient(new Chrome());
        web.addJavascriptInterface(new Bridge(), "Android");
        web.loadUrl("https://" + HOST + "/index.html");
    }

    /** 本地资源拦截 + 外链交给系统浏览器 */
    private class Local extends WebViewClient {
        @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
            Uri u = r.getUrl();
            if (!HOST.equals(u.getHost())) return null;
            String p = u.getPath();
            if (p == null || p.isEmpty() || "/".equals(p)) p = "/index.html";
            String name = p.substring(1);
            try {
                return new WebResourceResponse(mime(name), "utf-8", getAssets().open(name));
            } catch (IOException e) {
                return null;
            }
        }
        @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
            Uri u = r.getUrl();
            if (HOST.equals(u.getHost())) return false;
            try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception ignored) {}
            return true;
        }
    }

    /** 导入课表时的系统文件选择器 */
    private class Chrome extends WebChromeClient {
        @Override public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
            if (fileCb != null) fileCb.onReceiveValue(null);
            fileCb = cb;
            try {
                startActivityForResult(p.createIntent(), REQ_FILE);
                return true;
            } catch (Exception e) {
                fileCb = null;
                return false;
            }
        }
    }

    /** JS 里的 dl() 在 App 内走 SAF 保存（CSV / .ics 导出） */
    private class Bridge {
        @JavascriptInterface public void save(String name, String mime, String text) {
            runOnUiThread(() -> {
                saveName = (name == null || name.isEmpty()) ? "export.txt" : name;
                saveMime = (mime == null || mime.isEmpty()) ? "text/plain" : mime.split(";")[0];
                saveText = text == null ? "" : text;
                Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType(saveMime);
                i.putExtra(Intent.EXTRA_TITLE, saveName);
                try {
                    startActivityForResult(i, REQ_SAVE);
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "此系统不支持文件保存", Toast.LENGTH_SHORT).show();
                }
            });
        }
    }

    @Override protected void onActivityResult(int req, int res, Intent data) {
        if (req == REQ_FILE) {
            if (fileCb == null) return;
            fileCb.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(res, data));
            fileCb = null;
        } else if (req == REQ_SAVE) {
            if (res == RESULT_OK && data != null && data.getData() != null) write(data.getData());
            else Toast.makeText(this, "已取消保存", Toast.LENGTH_SHORT).show();
        }
    }

    private void write(Uri uri) {
        try (OutputStream os = getContentResolver().openOutputStream(uri)) {
            if (os == null) throw new IOException("无法写入该位置");
            os.write(saveText.getBytes(StandardCharsets.UTF_8));
            Toast.makeText(this, "已保存 " + saveName, Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            Toast.makeText(this, "保存失败：" + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    /** 返回键：先关弹层，再退出 */
    @Override public void onBackPressed() {
        web.evaluateJavascript(
            "(function(){try{return (typeof onBack==='function'&&onBack())?'1':'0'}catch(e){return '0'}})()",
            v -> { if (!"\"1\"".equals(v)) finish(); });
    }
}
