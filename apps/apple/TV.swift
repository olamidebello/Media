import SwiftUI
import AVKit
struct Channel: Decodable, Identifiable { let id: Int; let name: String; let url: String; let category: String }
struct Guide: Decodable { let channels: [Channel] }
@main struct TVApp: App { var body: some Scene { WindowGroup { ChannelList() } } }
struct ChannelList: View {
 @State var channels: [Channel] = []
 @State var error = ""
 @State var player: AVPlayer?
 @State var selected = false
 var body: some View {
  NavigationStack {
   List {
    if !error.isEmpty { Text(error) }
    ForEach(channels) { c in
     Button(c.name + " · " + c.category) {
      if let u = URL(string:c.url), u.scheme == "https" { player = AVPlayer(url:u); selected = true }
     }
    }
   }
   .navigationTitle("Africa Media Hub")
   .task { await load() }
   .fullScreenCover(isPresented:$selected) {
    if let p = player { VideoPlayer(player:p).onAppear { p.play() }.onDisappear { p.pause() } }
   }
  }
 }
 func load() async {
  do {
   let (data,response) = try await URLSession.shared.data(from:URL(string:"https://media.africandroid.world/api/guide")!)
   guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }
   channels = try JSONDecoder().decode(Guide.self,from:data).channels
  } catch { self.error = "Channel guide unavailable. Reopen the app to retry." }
 }
}
