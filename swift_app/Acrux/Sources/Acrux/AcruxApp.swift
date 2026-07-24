import SwiftUI

@main
struct AcruxApp: App {
    @NSApplicationDelegateAdaptor(AcruxAppDelegate.self) var appDelegate
    @StateObject private var acrux = AcruxService()
    @StateObject private var chatStore = ChatStore()

    init() {
        // Wiring happens after object creation in body via onAppear-like is not possible here,
        // so we rely on a lazy assignment in the first view appearance.
    }

    var body: some Scene {
        WindowGroup {
            HomeView()
                .environmentObject(acrux)
                .environmentObject(chatStore)
                .onAppear {
                    appDelegate.acrux = acrux
                    appDelegate.configureStatusBar(acrux: acrux)
                    acrux.chatStore = chatStore
                }
        }
        .defaultSize(width: 1400, height: 900)
    }
}
