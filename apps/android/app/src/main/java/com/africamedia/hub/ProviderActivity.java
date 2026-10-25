package com.africamedia.hub;
import android.app.*;import android.os.*;import android.webkit.*;import android.net.Uri;
public class ProviderActivity extends Activity {
 WebView web;
 @Override public void onCreate(Bundle state){super.onCreate(state);String url=getIntent().getStringExtra("url");if(url==null||!"https".equals(Uri.parse(url).getScheme())){finish();return;}web=new WebView(this);setContentView(web);web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);web.setWebViewClient(new WebViewClient(){@Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return !"https".equals(r.getUrl().getScheme());}});web.loadUrl(url);}
 @Override public void onBackPressed(){if(web!=null&&web.canGoBack())web.goBack();else finish();}
 @Override protected void onDestroy(){if(web!=null)web.destroy();super.onDestroy();}
}
