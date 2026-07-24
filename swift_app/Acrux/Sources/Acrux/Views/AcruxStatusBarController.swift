import SwiftUI
import AppKit

@MainActor
final class AcruxStatusBarController: NSObject {
    private var statusItem: NSStatusItem?
    private weak var acrux: AcruxService?

    init(acrux: AcruxService?) {
        self.acrux = acrux
        super.init()
        setupStatusItem()
    }

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        statusItem?.button?.image = NSImage(systemSymbolName: "star.fill", accessibilityDescription: "Acrux")
        statusItem?.button?.imagePosition = .imageOnly
        statusItem?.menu = buildMenu()
    }

    private func buildMenu() -> NSMenu {
        let menu = NSMenu(title: "Acrux")
        menu.addItem(withTitle: "Show Acrux", action: #selector(showMainWindow), keyEquivalent: "")
        menu.addItem(withTitle: "Toggle floating widget", action: #selector(toggleFloatingWidget), keyEquivalent: "")
        menu.addItem(NSMenuItem.separator())
        menu.addItem(withTitle: "New chat", action: #selector(newChat), keyEquivalent: "")
        menu.addItem(withTitle: acrux?.isBackendRunning == true ? "Stop Acrux" : "Start Acrux", action: #selector(toggleBackend), keyEquivalent: "")
        menu.addItem(NSMenuItem.separator())
        menu.addItem(withTitle: "Quit", action: #selector(quit), keyEquivalent: "q")
        return menu
    }

    func refreshMenu() {
        statusItem?.menu = buildMenu()
    }

    @objc private func showMainWindow() {
        NSApp.activate(ignoringOtherApps: true)
        NSApp.windows.first?.makeKeyAndOrderFront(nil)
    }

    @objc private func toggleFloatingWidget() {
        if let panel = FloatingPanelController.shared, panel.isVisible {
            panel.close()
        } else {
            let panel = FloatingPanelController()
            panel.center()
            panel.orderFront(nil)
        }
    }

    @objc private func newChat() {
        NotificationCenter.default.post(name: Notification.Name("acruxNewChat"), object: nil)
    }

    @objc private func toggleBackend() {
        if acrux?.isBackendRunning == true {
            acrux?.stopBackend()
        } else {
            acrux?.startBackend()
        }
        refreshMenu()
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }
}
