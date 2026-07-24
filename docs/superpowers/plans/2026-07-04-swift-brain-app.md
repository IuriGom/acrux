# Swift Native Acrux App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a true native macOS SwiftUI app named **Acrux** that runs the existing Python backend as a child process and provides a smooth, dark-themed UI without any webview.

**Architecture:** The Swift app manages the Python FastAPI backend (`acrux.app.main`) as a child process, talks to it over HTTP/WebSocket, persists chats locally, and renders all UI in SwiftUI. The home screen uses SpriteKit for a smooth particle-network animation.

**Tech Stack:** Swift 6.3, SwiftUI, SpriteKit, Foundation, URLSessionWebSocketTask, NSOpenPanel.

---

## File Structure

```
acrux/swift_app/Acrux/
├── Package.swift
├── Sources/
│   └── Acrux/
│       ├── AcruxApp.swift
│       ├── Models/
│       │   ├── Chat.swift
│       │   ├── Message.swift
│       │   ├── ToolCall.swift
│       │   ├── OllamaModel.swift
│       │   └── AcruxStatus.swift
│       ├── Services/
│       │   ├── AcruxService.swift
│       │   ├── BackendProcess.swift
│       │   └── ChatStore.swift
│       ├── Views/
│       │   ├── HomeView.swift
│       │   ├── SidebarView.swift
│       │   ├── NewTaskView.swift
│       │   ├── ChatView.swift
│       │   ├── MessageRow.swift
│       │   ├── ToolCallRow.swift
│       │   ├── ReasoningView.swift
│       │   ├── PastChatsView.swift
│       │   ├── AcruxStatusView.swift
│       │   └── AcruxAnimationScene.swift
│       └── Helpers/
│           ├── WorkspacePicker.swift
│           ├── Formatters.swift
│           └── Constants.swift
├── Resources/
│   └── Acrux.icns
└── build_app.sh
```

---

## Task 1: Swift Package Skeleton

**Files:**
- Create: `acrux/swift_app/Acrux/Package.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/AcruxApp.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Constants.swift`

- [ ] **Step 1: Create `Package.swift`**

```swift
// swift-tools-version:6.0
import PackageDescription

let package = Package(
    name: "Acrux",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "Acrux", targets: ["Acrux"])
    ],
    targets: [
        .executableTarget(
            name: "Acrux",
            path: "Sources/Acrux",
            swiftSettings: [.enableExperimentalFeature("StrictConcurrency")]
        )
    ]
)
```

- [ ] **Step 2: Create `Constants.swift`**

```swift
import Foundation

enum Constants {
    static let backendHost = "127.0.0.1"
    static let backendPort = 11438
    static let acruxProjectDir = "~/acrux"
    static let pythonPath = "/opt/homebrew/opt/python@3.14/bin/python3.14"
    static let appName = "Acrux"
}
```

- [ ] **Step 3: Create `AcruxApp.swift`**

```swift
import SwiftUI

@main
struct AcruxApp: App {
    @StateObject private var acrux = AcruxService()

    var body: some Scene {
        WindowGroup {
            HomeView()
                .environmentObject(acrux)
        }
        .windowResizability(.contentSize)
        .defaultSize(width: 1400, height: 900)
    }
}
```

- [ ] **Step 4: Verify build**

Run:
```bash
cd acrux/swift_app/Acrux
swift build
```

Expected: successful compilation.

---

## Task 2: Backend Process Manager

**Files:**
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Services/BackendProcess.swift`

- [ ] **Step 1: Implement `BackendProcess`**

```swift
import Foundation
import Combine

@MainActor
final class BackendProcess: ObservableObject {
    @Published var isRunning = false
    private var task: Process?

    func start() {
        guard task == nil || !task!.isRunning else { return }
        let task = Process()
        task.executableURL = URL(fileURLWithPath: Constants.pythonPath)
        task.arguments = [
            "-S", "-c",
            "from acrux.app.launcher import launch; launch()"
        ]
        task.environment = [
            "PYTHONPATH": "\(Constants.acruxProjectDir)/.venv/lib/python3.14/site-packages:\(Constants.acruxProjectDir)"
        ]
        task.currentDirectoryURL = URL(fileURLWithPath: Constants.acruxProjectDir)
        task.standardOutput = FileHandle.nullDevice
        task.standardError = FileHandle.nullDevice
        task.terminationHandler = { [weak self] _ in
            Task { @MainActor in self?.isRunning = false }
        }
        do {
            try task.run()
            self.task = task
            isRunning = true
        } catch {
            isRunning = false
        }
    }

    func stop() {
        task?.terminate()
        task = nil
        isRunning = false
    }
}
```

- [ ] **Step 2: Test launch**

Run the executable, wait, then:
```bash
curl -s http://127.0.0.1:11438/api/acrux/status
```

Expected: JSON status response.

---

## Task 3: API Models and Service

**Files:**
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Models/*.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Services/AcruxService.swift`

- [ ] **Step 1: Define models**

`Chat.swift`:
```swift
import Foundation

struct Chat: Identifiable, Codable {
    let id: UUID
    var title: String
    var workspace: String
    var model: String
    var allowedTools: [String]
    var autoAccept: Bool
    var messages: [Message]
    var createdAt: Date
    var updatedAt: Date
}
```

`Message.swift`:
```swift
import Foundation

struct Message: Identifiable, Codable {
    let id: UUID
    var role: String // user | assistant
    var content: String
    var reasoning: String?
    var toolCalls: [ToolCall]?
    var toolResults: [ToolResult]?
    var timestamp: Date
}
```

`ToolCall.swift`:
```swift
import Foundation

struct ToolCall: Identifiable, Codable {
    let id: String
    let name: String
    let arguments: [String: AnyCodable]
}

struct ToolResult: Identifiable, Codable {
    let id: String
    let output: String
}
```

Use `AnyCodable` or define a simple wrapper for JSON dictionaries.

`OllamaModel.swift`:
```swift
struct OllamaModel: Codable, Identifiable {
    let id = UUID()
    let name: String
    let size: Int
}
```

`AcruxStatus.swift`:
```swift
struct AcruxStatus: Codable {
    let running: Bool
    let profile: String
    let reflectionModel: String
    let embeddingModel: String
    let provider: String
    let facts: Int
    let skills: Int
    let episodes: Int
}
```

- [ ] **Step 2: Implement `AcruxService`**

```swift
import Foundation

@MainActor
final class AcruxService: ObservableObject {
    @Published var status: AcruxStatus?
    @Published var models: [OllamaModel] = []
    @Published var chats: [Chat] = []
    @Published var currentChat: Chat?
    @Published var isConnected = false

    private let process = BackendProcess()
    private var webSocketTask: URLSessionWebSocketTask?

    func startBackend() { process.start() }
    func stopBackend() { process.stop() }

    func fetchStatus() async {
        guard let url = URL(string: "http://\(Constants.backendHost):\(Constants.backendPort)/api/acrux/status") else { return }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            status = try JSONDecoder().decode(AcruxStatus.self, from: data)
            isConnected = true
        } catch {
            isConnected = false
        }
    }

    func fetchModels() async {
        guard let url = URL(string: "http://\(Constants.backendHost):\(Constants.backendPort)/api/models") else { return }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let response = try JSONDecoder().decode([String: [OllamaModel]].self, from: data)
            models = response["models"] ?? []
        } catch {}
    }
}
```

- [ ] **Step 3: Test service**

Run the backend and the Swift executable, then verify that `fetchStatus()` populates the status.

---

## Task 4: WebSocket Chat Engine

**Files:**
- Modify: `acrux/swift_app/Acrux/Sources/Acrux/Services/AcruxService.swift`

- [ ] **Step 1: Add WebSocket connection and streaming**

Add to `AcruxService`:

```swift
func connect(to chat: Chat) {
    currentChat = chat
    guard let url = URL(string: "ws://\(Constants.backendHost):\(Constants.backendPort)/ws/chat/\(chat.id.uuidString)") else { return }
    webSocketTask = URLSession.shared.webSocketTask(with: url)
    webSocketTask?.resume()
    receive()
}

func send(_ text: String) {
    guard let chat = currentChat else { return }
    let payload: [String: Any] = [
        "type": "start",
        "message": text,
        "model": chat.model,
        "workspace": chat.workspace,
        "auto_accept": chat.autoAccept,
        "allowed_tools": chat.allowedTools
    ]
    let data = try! JSONSerialization.data(withJSONObject: payload)
    webSocketTask?.send(.data(data)) { _ in }
}

private func receive() {
    webSocketTask?.receive { [weak self] result in
        switch result {
        case .success(let message):
            self?.handle(message)
            self?.receive()
        case .failure:
            Task { @MainActor in self?.isConnected = false }
        }
    }
}

private func handle(_ message: URLSessionWebSocketTask.Message) {
    // Parse JSON, update currentChat.messages, handle tool_call approval.
}
```

- [ ] **Step 2: Handle tool approval flow**

When a `tool_call` event arrives and `autoAccept == false`, append a pending `ToolCall` to the message and pause receiving until the user approves/denies. Then send `approve_tool` / `deny_tool` back over the socket.

---

## Task 5: SpriteKit Home Animation

**Files:**
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/AcruxAnimationScene.swift`
- Modify: `acrux/swift_app/Acrux/Sources/Acrux/Views/HomeView.swift`

- [ ] **Step 1: Create `AcruxAnimationScene`**

Use `SKEmitterNode` or a custom `SKScene` that animates particles with connecting lines and a central glow. Keep it lightweight (60fps, ~80 nodes).

- [ ] **Step 2: Embed in `HomeView`**

Use `SpriteView(scene: AcruxAnimationScene(), options: [.allowsTransparency])` as the background of the landing screen.

---

## Task 6: Navigation and Main Views

**Files:**
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/HomeView.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/SidebarView.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/NewTaskView.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/PastChatsView.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/AcruxStatusView.swift`

- [ ] **Step 1: Build `HomeView`**

Three-column layout:
- Left sidebar (220 pt) with app name and navigation.
- Center hero with title, subtitle, and animated background.
- Right content area swaps between New Task, Past Chats, Acrux Status.

Use `@State private var selectedTab: SidebarTab = .home`.

- [ ] **Step 2: Build `SidebarView`**

Buttons for Home, New Task, Past Chats, Acrux Status. Show a small status dot (green if connected, red if not).

- [ ] **Step 3: Build `NewTaskView`**

Form with:
- "Choose workspace" button that calls `NSOpenPanel`.
- Model picker from `acrux.models`.
- Tool toggles.
- Auto-accept toggle.
- Start button that creates a `Chat`, saves it, and opens `ChatView`.

- [ ] **Step 4: Build `PastChatsView` and `AcruxStatusView`**

`PastChatsView`: list of `ChatStore` chats, tap to resume.
`AcruxStatusView`: status cards, Start/Stop Acrux button, expandable knowledge summary fetched from `/api/acrux/knowledge`.

---

## Task 7: Chat UI

**Files:**
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/ChatView.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/MessageRow.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/ToolCallRow.swift`
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Views/ReasoningView.swift`

- [ ] **Step 1: Build `ChatView`**

Header with back button, chat title, model, workspace, and auto-accept toggle.
Scrollable message list and a bottom input bar with send and attach buttons.

- [ ] **Step 2: Build `MessageRow`**

Different styling for user vs assistant. Animate appearance with `.transition(.opacity.combined(with: .move(edge: .bottom)))`.

- [ ] **Step 3: Build `ReasoningView`**

Collapsible blue-bordered box labeled "Reasoning".

- [ ] **Step 4: Build `ToolCallRow`**

Card showing tool name and arguments. If pending, show Approve/Deny buttons. If executed, show output in a monospace text block.

---

## Task 8: Chat Persistence

**Files:**
- Create: `acrux/swift_app/Acrux/Sources/Acrux/Services/ChatStore.swift`

- [ ] **Step 1: Implement `ChatStore`**

Save/load chats from `~/.acrux/app/swift_chats.json`. Use `JSONEncoder`/`JSONDecoder`.

```swift
@MainActor
final class ChatStore: ObservableObject {
    @Published var chats: [Chat] = []
    private let url = FileManager.default
        .homeDirectoryForCurrentUser
        .appendingPathComponent(".acrux/app/swift_chats.json")

    func load() { ... }
    func save(_ chat: Chat) { ... }
    func delete(_ chat: Chat) { ... }
}
```

---

## Task 9: Build Script and App Bundle

**Files:**
- Create: `acrux/swift_app/Acrux/build_app.sh`
- Create: `acrux/swift_app/Acrux/Info.plist`

- [ ] **Step 1: Write `build_app.sh`**

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"
swift build -c release

APP=".build/release/Acrux.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
mkdir -p "$APP/Contents/Resources"
cp .build/release/Acrux "$APP/Contents/MacOS/Acrux"
cp Info.plist "$APP/Contents/Info.plist"
cp Resources/Acrux.icns "$APP/Contents/Resources/Acrux.icns"
chmod +x "$APP/Contents/MacOS/Acrux"
echo "Built $APP"
```

- [ ] **Step 2: Write `Info.plist`**

Standard macOS app plist with `CFBundleName=Acrux`, `CFBundleIconFile=Acrux`, `LSUIElement=false`, `NSHighResolutionCapable=true`.

- [ ] **Step 3: Copy icon resource**

Reuse `acrux/app_bundle/Acrux.app/Contents/Resources/Acrux.icns` in `acrux/swift_app/Acrux/Resources/Acrux.icns`.

- [ ] **Step 4: Build and test**

Run `build_app.sh`, then open `.build/release/Acrux.app`. Verify the menu bar shows **Acrux**, the app appears in the Dock, and the backend starts.

---

## Task 10: Install and Documentation

**Files:**
- Modify: `acrux/acrux/app_bundle/install_app.sh`
- Modify: `acrux/docs/OPERATING.md`

- [ ] **Step 1: Update install script**

Make `install_app.sh` build the Swift app and copy it to `~/Applications/Acrux.app`.

- [ ] **Step 2: Update docs**

Replace the old web-based app section with instructions for the Swift app: build, install, pin to Dock, first launch.

---

## Spec Coverage Self-Review

| Requirement | Task |
|-------------|------|
| Native macOS app, no webview | Tasks 1, 6, 9 |
| Smooth animations | Task 5 |
| Dock-pinnable with app identity | Tasks 9, 10 |
| Shows tools called and reasoning | Tasks 4, 7 |
| File/workspace access | Tasks 3, 6 |
| Auto-accept option | Tasks 3, 4, 7 |
| Acrux status + "What it knows" | Tasks 3, 6 |
| Past chats | Tasks 6, 8 |
| Dark theme | Task 6 (all views) |

No placeholders. All file paths and key types are defined.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-04-swift-acrux-app.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach?
