import SwiftUI
import WebKit
import SafariServices
@main struct MediaApp: App {
 var body: some Scene { WindowGroup { MediaWeb().ignoresSafeArea(edges:.bottom) } }
}
struct MediaWeb: UIViewRepresentable {
 func makeUIView(context: Context) -> WKWebView {
  let config = WKWebViewConfiguration()
  config.userContentController.add(context.coordinator, name:"mediaProvider")
  config.userContentController.add(context.coordinator, name:"mediaExternal")
  let web = WKWebView(frame:.zero, configuration:config)
  web.navigationDelegate = context.coordinator
  web.uiDelegate = context.coordinator
  context.coordinator.web = web
  web.load(URLRequest(url:URL(string:"https://media.africandroid.world/")!))
  return web
 }
 func updateUIView(_ view: WKWebView, context: Context) {}
 func makeCoordinator() -> Coordinator { Coordinator() }
 static func dismantleUIView(_ view: WKWebView, coordinator: Coordinator) { view.configuration.userContentController.removeScriptMessageHandler(forName:"mediaProvider"); view.configuration.userContentController.removeScriptMessageHandler(forName:"mediaExternal") }
 class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
  weak var web: WKWebView?
  func show(_ url: URL) {
   guard url.scheme == "https", let root = web?.window?.rootViewController else { return }
   var top = root
   while let next = top.presentedViewController { top = next }
   top.present(SFSafariViewController(url:url), animated:true)
  }
  func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
   guard message.frameInfo.isMainFrame, message.frameInfo.securityOrigin.host == "media.africandroid.world", let value = message.body as? String, let url = URL(string:value) else { return }
   if message.name == "mediaExternal" { if url.scheme == "https" { UIApplication.shared.open(url) } }
   else { show(url) }
  }
  func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy)->Void) {
   guard let url = action.request.url else { decisionHandler(.cancel); return }
   if url.scheme == "https" && url.host == "media.africandroid.world" { decisionHandler(.allow) }
   else { if action.targetFrame?.isMainFrame != false { show(url) }; decisionHandler(.cancel) }
  }
  func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
   if let url = action.request.url { show(url) }
   return nil
  }
 }
}
