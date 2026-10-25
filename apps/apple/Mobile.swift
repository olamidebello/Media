import SwiftUI
import WebKit
@main struct MediaApp: App {var body: some Scene {WindowGroup {MediaWeb().ignoresSafeArea(edges:.bottom)}}}
struct MediaWeb: UIViewRepresentable {
 func makeUIView(context:Context)->WKWebView {let w=WKWebView();w.navigationDelegate=context.coordinator;w.load(URLRequest(url:URL(string:"https://media.africandroid.world/")!));return w}
 func updateUIView(_ view:WKWebView,context:Context){}
 func makeCoordinator()->Coordinator {Coordinator()}
 class Coordinator:NSObject,WKNavigationDelegate {func webView(_ webView:WKWebView,decidePolicyFor action:WKNavigationAction,decisionHandler:@escaping(WKNavigationActionPolicy)->Void){guard let u=action.request.url else{decisionHandler(.cancel);return};if u.scheme=="https" && u.host=="media.africandroid.world" {decisionHandler(.allow)}else{if u.scheme=="https" {UIApplication.shared.open(u)};decisionHandler(.cancel)}}}
}
