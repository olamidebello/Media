import SwiftUI
import WebKit
import SafariServices
import Network
@main struct MediaApp: App {
 var body: some Scene { WindowGroup { MediaWeb().ignoresSafeArea(edges:.bottom) } }
}
struct MediaWeb: UIViewRepresentable {
 func makeUIView(context: Context) -> WKWebView {
  let config = WKWebViewConfiguration()
  config.userContentController.add(context.coordinator, name:"mediaProvider")
  config.userContentController.add(context.coordinator, name:"mediaExternal")
  config.userContentController.add(context.coordinator, name:"mediaCameraDiscovery")
  config.userContentController.addUserScript(WKUserScript(source:"window.MediaMobileCameras={discover:function(){window.webkit.messageHandlers.mediaCameraDiscovery.postMessage('discover');}};", injectionTime:.atDocumentStart, forMainFrameOnly:true))
  config.userContentController.add(context.coordinator, name:"mediaTVDiscovery")
  config.userContentController.addUserScript(WKUserScript(source:"window.MediaMobileTV={discover:function(){window.webkit.messageHandlers.mediaTVDiscovery.postMessage('discover');}};", injectionTime:.atDocumentStart, forMainFrameOnly:true))
  let web = WKWebView(frame:.zero, configuration:config)
  web.navigationDelegate = context.coordinator
  web.uiDelegate = context.coordinator
  context.coordinator.web = web
  web.load(URLRequest(url:URL(string:"https://media.africandroid.world/")!))
  return web
 }
 func updateUIView(_ view: WKWebView, context: Context) {}
 func makeCoordinator() -> Coordinator { Coordinator() }
 static func dismantleUIView(_ view: WKWebView, coordinator: Coordinator) { view.configuration.userContentController.removeScriptMessageHandler(forName:"mediaCameraDiscovery"); view.configuration.userContentController.removeScriptMessageHandler(forName:"mediaTVDiscovery"); view.configuration.userContentController.removeScriptMessageHandler(forName:"mediaProvider"); view.configuration.userContentController.removeScriptMessageHandler(forName:"mediaExternal") }
 class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
  weak var web: WKWebView?
  func show(_ url: URL) {
   guard url.scheme == "https", let root = web?.window?.rootViewController else { return }
   var top = root
   while let next = top.presentedViewController { top = next }
   top.present(SFSafariViewController(url:url), animated:true)
  }
  func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
   if message.name == "mediaCameraDiscovery" {
    guard message.frameInfo.isMainFrame, message.frameInfo.securityOrigin.protocol == "https", message.frameInfo.securityOrigin.host == "media.africandroid.world", let root = web?.window?.rootViewController else { return }
    var top = root
    while let next = top.presentedViewController { top = next }
    let picker = TVDiscoveryController()
    picker.cameraMode = true
    picker.onCameraSelect = { [weak self] name in
     guard let data = try? JSONSerialization.data(withJSONObject:["name":name,"address":"Bonjour camera"]), let json = String(data:data,encoding:.utf8) else { return }
     self?.web?.evaluateJavaScript("window.mediaCameraDiscovered&&window.mediaCameraDiscovered("+json+")",completionHandler:nil)
    }
    top.present(UINavigationController(rootViewController:picker), animated:true)
    return
   }
   if message.name == "mediaTVDiscovery" {
    guard message.frameInfo.isMainFrame, message.frameInfo.securityOrigin.protocol == "https", message.frameInfo.securityOrigin.host == "media.africandroid.world", web?.url?.path == "/install", let root = web?.window?.rootViewController else { return }
    var top = root
    while let next = top.presentedViewController { top = next }
    let picker = TVDiscoveryController()
    picker.onSelect = { [weak self] platform in self?.web?.load(URLRequest(url:URL(string:"https://media.africandroid.world/install?tvPlatform="+platform)!)) }
    top.present(UINavigationController(rootViewController:picker), animated:true)
    return
   }
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


final class TVDiscoveryController: UITableViewController {
 var cameraMode = false
 var onCameraSelect: ((String)->Void)?
 var onSelect: ((String)->Void)?
 private var browsers: [NWBrowser] = []
 private var devices: [(name:String, platform:String)] = []
 private var keys = Set<String>()
 private var stopped = false
 private var timeout: DispatchWorkItem?
 override func viewDidLoad() {
  super.viewDidLoad()
  title = cameraMode ? "Nearby camera services" : "Nearby TVs"
  navigationItem.leftBarButtonItem = UIBarButtonItem(barButtonSystemItem:.done, target:self, action:#selector(done))
  let label = UILabel()
  label.numberOfLines = 0
  label.text = "Connect to the same Wi-Fi as your TV and allow Local Network access. Searching for 12 seconds. Select a device for installation options. Cast/AirPlay receivers may not identify the TV OS; confirm it on the next page. TV approval is required."
  label.frame = CGRect(x:16,y:0,width:320,height:170)
  if cameraMode { label.text = "Connect to camera Wi-Fi and allow Local Network access. Searching advertised RTSP/ONVIF Bonjour services. This cannot discover all cameras. Select a service, confirm its name, and pair a local gateway for remote snapshots." }
  tableView.tableHeaderView = label
  let tvTypes = [("_googlecast._tcp","android"),("_androidtvremote2._tcp","android"),("_adb-tls-connect._tcp","android"),("_airplay._tcp","apple"),("_webostv._tcp","lg"),("_roku-ecp._tcp","roku")]
  let types = cameraMode ? [("_rtsp._tcp","camera"),("_onvif._tcp","camera")] : tvTypes
  for (type, platform) in types {
   let params = NWParameters.tcp
   params.requiredInterfaceType = .wifi
   let browser = NWBrowser(for:.bonjour(type:type,domain:"local."),using:params)
   browser.browseResultsChangedHandler = { [weak self] results, _ in
    guard let self = self, !self.stopped else { return }
    for result in results {
     if case let .service(name,_,_,_) = result.endpoint {
      let key = name+":"+platform
      if self.keys.insert(key).inserted {
       self.devices.append((name,platform))
      }
     }
    }
    self.tableView.reloadData()
   }
   browser.stateUpdateHandler = { [weak self] state in
    if case .waiting = state { self?.navigationItem.prompt = "Allow Local Network access in Settings if discovery is blocked." }
   }
   browsers.append(browser)
   browser.start(queue:.main)
  }
  let work = DispatchWorkItem { [weak self] in
   guard let self = self else { return }
   self.stop()
   self.navigationItem.prompt = self.devices.isEmpty ? "No TVs found. Check Wi-Fi and Local Network access." : "Select a device to choose installation options."
  }
  timeout = work
  DispatchQueue.main.asyncAfter(deadline:.now()+12,execute:work)
 }
 private func stop() { stopped = true; for browser in browsers { browser.cancel() }; browsers.removeAll(); timeout?.cancel() }
 @objc private func done() { stop(); dismiss(animated:true) }
 override func viewDidDisappear(_ animated:Bool) { super.viewDidDisappear(animated); stop() }
 override func tableView(_ tableView:UITableView,numberOfRowsInSection section:Int)->Int { devices.count }
 override func tableView(_ tableView:UITableView,cellForRowAt indexPath:IndexPath)->UITableViewCell {
  let cell = UITableViewCell(style:.subtitle,reuseIdentifier:nil)
  cell.textLabel?.text = devices[indexPath.row].name
  cell.detailTextLabel?.text = "Platform estimate: "+devices[indexPath.row].platform
  return cell
 }
 override func tableView(_ tableView:UITableView,didSelectRowAt indexPath:IndexPath) {
  let platform = devices[indexPath.row].platform
  let name = devices[indexPath.row].name
  stop()
  dismiss(animated:true) { if self.cameraMode { self.onCameraSelect?(name) } else { self.onSelect?(platform) } }
 }
}
