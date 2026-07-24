import SwiftUI
import AppKit

@MainActor
final class AcruxAppDelegate: NSObject, NSApplicationDelegate {
    var acrux: AcruxService?
    private var statusBarController: AcruxStatusBarController?

    func applicationDidFinishLaunching(_ notification: Notification) {
        configureStatusBar(acrux: acrux)
    }

    func configureStatusBar(acrux: AcruxService?) {
        guard statusBarController == nil else { return }
        statusBarController = AcruxStatusBarController(acrux: acrux)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        acrux?.stopBackend()
    }
}
