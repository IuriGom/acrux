import SwiftUI
import SpriteKit

struct KnowledgeGraphView: View {
    @EnvironmentObject var acrux: AcruxService
    @State private var project = ""
    @State private var graph: GraphResponse?
    @State private var selectedNode: GraphNode?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showFilters = false
    @State private var visibleTypes: Set<String> = ["acrux", "project", "cluster", "fact", "episode", "skill"]
    @State private var sceneSize: CGSize = CGSize(width: 1200, height: 800)
    @State private var fitRequest = UUID()
    @State private var scene: KnowledgeGraphScene?
    @State private var splashActive = false

    private var projects: [String] {
        let fm = FileManager.default
        let projectsDir = (acrux.status?.dataDir ?? "\(NSHomeDirectory())/.acrux/data").appending("/projects")
        guard let urls = try? fm.contentsOfDirectory(at: URL(fileURLWithPath: projectsDir), includingPropertiesForKeys: nil, options: .skipsHiddenFiles) else {
            return []
        }
        return urls.filter { $0.hasDirectoryPath }.map { $0.lastPathComponent }.sorted()
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Picker("Project", selection: $project) {
                    Text("Global Acrux").tag("")
                    ForEach(projects, id: \.self) { p in
                        Text(p).tag(p)
                    }
                }
                .pickerStyle(.menu)
                .frame(width: 220)

                Spacer()

                Button {
                    showFilters.toggle()
                } label: {
                    Image(systemName: "line.3.horizontal.decrease.circle")
                        .font(.system(size: 16, weight: .semibold))
                }
                .buttonStyle(AnimatedIconButtonStyle())
                .foregroundStyle(.primary)

                Button {
                    Task { await loadGraph() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 14, weight: .semibold))
                }
                .buttonStyle(AnimatedIconButtonStyle())
                .foregroundStyle(Color.acruxAccent)
                .disabled(isLoading)

                Button {
                    fitRequest = UUID()
                } label: {
                    Image(systemName: "arrow.up.left.and.arrow.down.right")
                        .font(.system(size: 14, weight: .semibold))
                }
                .buttonStyle(AnimatedIconButtonStyle())
                .foregroundStyle(Color.acruxAccent)
                .help("Fit graph to view")

                HStack(spacing: 4) {
                    Button {
                        NotificationCenter.default.post(name: .zoomKnowledgeGraphOut, object: nil)
                    } label: {
                        Image(systemName: "minus.magnifyingglass")
                            .font(.system(size: 14, weight: .semibold))
                    }
                    .buttonStyle(AnimatedIconButtonStyle())
                    .foregroundStyle(.primary)
                    .help("Zoom out")

                    Button {
                        NotificationCenter.default.post(name: .zoomKnowledgeGraphIn, object: nil)
                    } label: {
                        Image(systemName: "plus.magnifyingglass")
                            .font(.system(size: 14, weight: .semibold))
                    }
                    .buttonStyle(AnimatedIconButtonStyle())
                    .foregroundStyle(.primary)
                    .help("Zoom in")
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
            .background(.ultraThinMaterial)

            GeometryReader { geometry in
                ZStack {
                    if let scene = scene {
                        AcruxSpriteView(
                            scene: scene,
                            fitRequest: fitRequest,
                            onNodeTap: { node in
                                Task { @MainActor in
                                    selectedNode = node
                                }
                            }
                        )
                        .ignoresSafeArea()
                        .onAppear {
                            sceneSize = geometry.size
                        }
                        .onChange(of: geometry.size) { _, newSize in
                            sceneSize = newSize
                        }
                        .transition(.scale(scale: 0.96).combined(with: .opacity))

                        if splashActive {
                            splashOverlay(geometry: geometry)
                        }
                    } else if isLoading {
                        ProgressView("Loading graph…")
                            .controlSize(.large)
                    } else if let errorMessage = errorMessage {
                        VStack(spacing: 12) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.system(size: 40))
                                .foregroundStyle(.secondary)
                            Text(errorMessage)
                                .foregroundStyle(.secondary)
                                .multilineTextAlignment(.center)
                        }
                        .frame(maxWidth: 320)
                    } else {
                        VStack(spacing: 12) {
                            Image(systemName: "circle.hexagongrid")
                                .font(.system(size: 48))
                                .foregroundStyle(.secondary)
                            Text("No memories to visualize yet.")
                                .foregroundStyle(.secondary)
                        }
                    }

                    if showFilters {
                        filterPanel
                            .transition(.move(edge: .trailing).combined(with: .opacity))
                    }

                    if let selectedNode = selectedNode {
                        nodeDetailPanel(node: selectedNode)
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                    }
                }
            }
        }
        .background(Color.acruxBg)
        .onAppear {
            Task { await loadGraph() }
        }
        .onChange(of: project) { _, _ in
            Task { await loadGraph() }
        }
        .onChange(of: visibleTypes) { _, _ in
            if let graph = graph {
                rebuildScene(graph: graph, size: sceneSize)
            }
        }
    }

    private var filterPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Visible types")
                    .font(.system(size: 14, weight: .bold))
                Spacer()
                Button {
                    withAnimation { showFilters = false }
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                }
                .buttonStyle(.plain)
            }

            ForEach(["acrux", "project", "cluster", "fact", "episode", "skill"], id: \.self) { type in
                Toggle(type.capitalized, isOn: Binding(
                    get: { visibleTypes.contains(type) },
                    set: { isOn in
                        if isOn {
                            visibleTypes.insert(type)
                        } else {
                            visibleTypes.remove(type)
                        }
                    }
                ))
                .toggleStyle(.checkbox)
            }
        }
        .padding(16)
        .frame(width: 180)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.25), radius: 20, x: 0, y: 10)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topTrailing)
        .padding(20)
    }

    private func nodeDetailPanel(node: GraphNode) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Circle()
                    .fill(Color(hex: node.color) ?? .white)
                    .frame(width: 12, height: 12)
                Text(node.type.capitalized)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                Spacer()
                Button {
                    withAnimation { selectedNode = nil }
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                }
                .buttonStyle(AnimatedIconButtonStyle())
            }

            Text(node.label)
                .font(.system(size: 16, weight: .bold))

            Text(node.contentSnippet)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(4)
                .multilineTextAlignment(.leading)

            if node.type == "fact", let factId = node.meta?["fact_id"]?.value as? Int {
                Button("Open in Memory Inspector") {
                    let project = node.meta?["project"]?.value as? String ?? "global"
                    NotificationCenter.default.post(
                        name: .openMemoryFactTree,
                        object: ["id": String(factId), "project": project]
                    )
                    withAnimation { selectedNode = nil }
                }
                .buttonStyle(GraphiteButtonStyle())
                .controlSize(.small)
            }

            Spacer()
        }
        .padding(16)
        .frame(width: 280, height: 180)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.25), radius: 20, x: 0, y: 10)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomLeading)
        .padding(20)
    }

    private func loadGraph() async {
        isLoading = true
        errorMessage = nil
        selectedNode = nil
        do {
            graph = try await acrux.fetchGraph(project: project)
            if graph == nil {
                errorMessage = project.isEmpty ? "Could not load global graph." : "Could not load graph for \(project)."
                scene = nil
            } else if graph?.nodes.isEmpty == true {
                errorMessage = project.isEmpty ? "No memories in the global graph yet." : "No memories found for \(project)."
                scene = nil
            } else if let graph = graph {
                rebuildScene(graph: graph, size: sceneSize)
            }
        } catch {
            errorMessage = "Failed to load graph: \(error.localizedDescription)"
            scene = nil
        }
        isLoading = false
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            withAnimation(.easeOut(duration: 0.7)) {
                splashActive = true
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.75) {
                splashActive = false
            }
        }
    }

    private func rebuildScene(graph: GraphResponse, size: CGSize) {
        let newScene = KnowledgeGraphScene(size: size)
        newScene.scaleMode = .resizeFill
        newScene.backgroundColor = .clear
        newScene.configure(graph: graph, visibleTypes: visibleTypes) { _ in }
        scene = newScene
    }

    @ViewBuilder
    private func splashOverlay(geometry: GeometryProxy) -> some View {
        ZStack {
            RadialGradient(
                colors: [.clear, Color.acruxAccent.opacity(0.25), .clear],
                center: .center,
                startRadius: 0,
                endRadius: geometry.size.width * 0.6
            )
            .scaleEffect(splashActive ? 2.2 : 0.2)
            .opacity(splashActive ? 0 : 1)

            Circle()
                .stroke(Color.acruxAccent.opacity(0.6), lineWidth: 2)
                .frame(width: 120, height: 120)
                .scaleEffect(splashActive ? 3.5 : 0.3)
                .opacity(splashActive ? 0 : 1)

            Image(systemName: "circle.hexagongrid")
                .font(.system(size: 42, weight: .bold))
                .foregroundStyle(Color.acruxAccent)
                .scaleEffect(splashActive ? 1.6 : 0.6)
                .opacity(splashActive ? 0 : 1)
        }
        .frame(width: geometry.size.width, height: geometry.size.height)
        .allowsHitTesting(false)
    }
}

// MARK: - SpriteKit host

/// A custom SKView subclass that guarantees it accepts first responder and forwards
/// input events to the SpriteKit scene. SwiftUI's default SKView wrapper often loses
/// scroll/pinch events because SKView does not reliably become first responder.
final class AcruxSKView: SKView {
    override var acceptsFirstResponder: Bool { true }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        if window != nil {
            window?.acceptsMouseMovedEvents = true
            DispatchQueue.main.async { [weak self] in
                _ = self?.becomeFirstResponder()
            }
        }
    }

    override func mouseMoved(with event: NSEvent) {
        (scene as? KnowledgeGraphScene)?.mouseMoved(with: event)
    }

    override func becomeFirstResponder() -> Bool {
        let ok = super.becomeFirstResponder()
        (scene as? KnowledgeGraphScene)?.logInput("AcruxSKView becomeFirstResponder ok=\(ok)")
        return ok
    }

    override func scrollWheel(with event: NSEvent) {
        logInput("AcruxSKView scrollWheel deltaY=\(event.scrollingDeltaY)")
        (scene as? KnowledgeGraphScene)?.scrollWheel(with: event)
    }

    override func magnify(with event: NSEvent) {
        logInput("AcruxSKView magnify mag=\(event.magnification)")
        (scene as? KnowledgeGraphScene)?.magnify(with: event)
    }

    override func mouseDown(with event: NSEvent) {
        (scene as? KnowledgeGraphScene)?.mouseDown(with: event)
    }

    override func mouseDragged(with event: NSEvent) {
        (scene as? KnowledgeGraphScene)?.mouseDragged(with: event)
    }

    override func mouseUp(with event: NSEvent) {
        (scene as? KnowledgeGraphScene)?.mouseUp(with: event)
    }

    private func logInput(_ message: String) {
        let logURL = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/Acrux/kg_input.log")
        try? FileManager.default.createDirectory(at: logURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        let entry = "\(Date()): \(message)\n"
        if let data = entry.data(using: .utf8) {
            if FileManager.default.fileExists(atPath: logURL.path),
               let handle = try? FileHandle(forWritingTo: logURL) {
                handle.seekToEndOfFile()
                handle.write(data)
                handle.closeFile()
            } else {
                try? data.write(to: logURL)
            }
        }
    }
}

struct AcruxSpriteView: NSViewRepresentable {
    let scene: KnowledgeGraphScene
    var fitRequest: UUID?
    var onNodeTap: (GraphNode) -> Void

    func makeNSView(context: Context) -> AcruxSKView {
        let view = AcruxSKView()
        view.allowsTransparency = true
        view.presentScene(scene)
        DispatchQueue.main.async {
            let ok = view.window?.makeFirstResponder(view) ?? false
            self.scene.logInput("makeNSView makeFirstResponder ok=\(ok)")
        }
        return view
    }

    func updateNSView(_ nsView: AcruxSKView, context: Context) {
        if nsView.scene !== scene {
            nsView.presentScene(scene)
        }
        if let scene = nsView.scene as? KnowledgeGraphScene {
            scene.fitRequest = fitRequest
            scene.nodeTapped = onNodeTap
        }
        let ok = nsView.window?.makeFirstResponder(nsView) ?? false
        scene.logInput("updateNSView makeFirstResponder ok=\(ok)")
        if !ok {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak nsView] in
                _ = nsView?.window?.makeFirstResponder(nsView!)
            }
        }
    }
}

// MARK: - SpriteKit scene

final class KnowledgeGraphScene: SKScene {
    private var graph: GraphResponse?
    private var visibleTypes: Set<String> = []
    var nodeTapped: ((GraphNode) -> Void)?
    private var nodeSprites: [String: SKSpriteNode] = [:]
    private var labelSprites: [String: SKLabelNode] = [:]
    private let cameraNode = SKCameraNode()
    private var isPanning = false
    private var isDraggingNode = false
    private var draggedNode: SKSpriteNode?
    private var draggedNodeId: String?
    private var hoveredNodeId: String?
    private var childTargets: [String: CGPoint] = [:]
    private var lastUpdateTime: TimeInterval = 0
    private var lastPanLocation: CGPoint = .zero
    private var dragStartLocation: CGPoint = .zero
    private var notificationObservers: [NSObjectProtocol] = []

    var fitRequest: UUID?
    private var lastFitRequest: UUID?
    private var hasCompletedInitialFit = false

    func configure(graph: GraphResponse, visibleTypes: Set<String>, nodeTapped: @escaping (GraphNode) -> Void) {
        self.graph = graph
        self.visibleTypes = visibleTypes
        self.nodeTapped = nodeTapped
    }

    override func didMove(to view: SKView) {
        super.didMove(to: view)
        logInput("didMove size=\(size.width)x\(size.height)")
        addChild(cameraNode)
        self.camera = cameraNode
        view.window?.makeFirstResponder(view)
        guard let graph = graph else { return }
        buildGraph(graph: graph)
        fitIfSized()

        notificationObservers.append(NotificationCenter.default.addObserver(
            forName: .zoomKnowledgeGraphIn,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.applyZoom(factor: 0.8)
            }
        })

        notificationObservers.append(NotificationCenter.default.addObserver(
            forName: .zoomKnowledgeGraphOut,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.applyZoom(factor: 1.25)
            }
        })
    }

    override func update(_ currentTime: TimeInterval) {
        super.update(currentTime)
        if let fitRequest = fitRequest, fitRequest != lastFitRequest {
            lastFitRequest = fitRequest
            logInput("update fitRequest triggered")
            fitToGraph(animated: true)
        }
        // Ease retargeted children toward their drag targets with a spring.
        let dt = lastUpdateTime == 0 ? 1.0 / 60.0 : min(0.1, currentTime - lastUpdateTime)
        lastUpdateTime = currentTime
        if !childTargets.isEmpty {
            let spring = 1 - exp(-dt * 14)
            var settled: [String] = []
            var moving: Set<String> = []
            for (id, target) in childTargets {
                guard let sprite = nodeSprites[id] else {
                    settled.append(id)
                    continue
                }
                let dx = target.x - sprite.position.x
                let dy = target.y - sprite.position.y
                if abs(dx) < 0.5 && abs(dy) < 0.5 {
                    sprite.position = target
                    settled.append(id)
                    moving.insert(id)
                } else {
                    sprite.position = CGPoint(x: sprite.position.x + dx * spring, y: sprite.position.y + dy * spring)
                    moving.insert(id)
                }
            }
            for id in settled {
                childTargets.removeValue(forKey: id)
            }
            if let draggedNodeId = draggedNodeId {
                moving.insert(draggedNodeId)
            }
            updateEdges(for: moving)
        }

        // Labels: acrux/project/cluster names stay visible; memory titles show
        // only on hover. World scale grows with camera scale so on-screen size
        // stays constant (SpriteKit camera scale is inverse).
        let cameraScale = max(0.001, cameraNode.xScale)
        for (nodeId, label) in labelSprites {
            guard let sprite = nodeSprites[nodeId],
                  let node = sprite.userData?["node"] as? GraphNode else { continue }
            let important = node.type == "acrux" || node.type == "project" || node.type == "cluster"
            label.isHidden = !(important || nodeId == hoveredNodeId)
            let baseScreenSize: CGFloat
            switch node.type {
            case "acrux": baseScreenSize = 0.44
            case "project": baseScreenSize = 0.44
            case "cluster": baseScreenSize = 0.42
            default: baseScreenSize = 0.55
            }
            label.setScale(baseScreenSize * cameraScale)
        }
    }

    override func didChangeSize(_ oldSize: CGSize) {
        super.didChangeSize(oldSize)
        logInput("didChangeSize old=\(oldSize.width)x\(oldSize.height) new=\(size.width)x\(size.height)")
        guard size.width > 0 && size.height > 0 && oldSize != size else { return }
        // Ignore small resizes (e.g. detail panel appearing) so the camera stays put.
        let widthDelta = abs(size.width - oldSize.width)
        let heightDelta = abs(size.height - oldSize.height)
        if widthDelta > 50 || heightDelta > 50 || !hasCompletedInitialFit {
            fitToGraph(animated: false)
        }
    }

    private func fitIfSized() {
        if size.width > 0 && size.height > 0 {
            fitToGraph(animated: false)
        } else {
            run(SKAction.wait(forDuration: 0.05)) { [weak self] in
                self?.fitIfSized()
            }
        }
    }

    override func willMove(from view: SKView) {
        super.willMove(from: view)
        for observer in notificationObservers {
            NotificationCenter.default.removeObserver(observer)
        }
        notificationObservers.removeAll()
    }

    private func buildGraph(graph: GraphResponse) {
        removeAllChildren()
        removeAllActions()
        nodeSprites.removeAll()
        labelSprites.removeAll()

        // Re-add camera after removeAllChildren.
        addChild(cameraNode)
        self.camera = cameraNode

        let visibleNodes = graph.nodes.filter { visibleTypes.contains($0.type) }
        let visibleNodeIds = Set(visibleNodes.map(\.id))
        let visibleEdges = graph.edges.filter { visibleNodeIds.contains($0.source) && visibleNodeIds.contains($0.target) }

        // Create high-quality sprite nodes backed by rendered circle textures.
        for (index, node) in visibleNodes.enumerated() {
            let radius = CGFloat(node.size)
            let color = SKColor(hex: node.color) ?? .white
            let sprite = makeCircleSprite(radius: radius, fillColor: color, strokeColor: .white, lineWidth: 1.5)
            sprite.position = CGPoint(x: node.x, y: node.y)
            sprite.name = node.id
            sprite.userData = NSMutableDictionary()
            sprite.userData?["node"] = node

            let importantTypes = Set(["acrux", "project", "cluster"])
            let shouldShowLabel = importantTypes.contains(node.type)
            let labelText = truncatedLabel(node.label, maxChars: node.type == "acrux" ? 40 : (node.type == "project" ? 18 : 26))
            let label = SKLabelNode(text: labelText)
            label.fontName = validSpriteKitFontName()
            // Render large and counter-scale in update() so text stays crisp.
            switch node.type {
            case "acrux": label.fontSize = 46
            case "project": label.fontSize = 30
            case "cluster": label.fontSize = 26
            default: label.fontSize = 20
            }
            label.fontColor = .white
            // Place project labels radially outward from the acrux center to avoid overlap.
            if node.type == "project" {
                let angle = atan2(sprite.position.y, sprite.position.x)
                let offset = radius + 10
                label.position = CGPoint(x: cos(angle) * offset, y: sin(angle) * offset)
                label.horizontalAlignmentMode = abs(cos(angle)) < 0.1 ? .center : (cos(angle) > 0 ? .left : .right)
                label.verticalAlignmentMode = abs(sin(angle)) < 0.1 ? .center : (sin(angle) > 0 ? .bottom : .top)
            } else {
                label.position = CGPoint(x: 0, y: -radius - 6)
                label.horizontalAlignmentMode = .center
                label.verticalAlignmentMode = .top
            }
            label.isHidden = !shouldShowLabel
            sprite.addChild(label)

            addChild(sprite)
            nodeSprites[node.id] = sprite
            labelSprites[node.id] = label

            // Entrance animation: scale up from zero with a slight stagger.
            sprite.setScale(0)
            let delay = SKAction.wait(forDuration: 0.02 + Double(index) * 0.015)
            let grow = SKAction.scale(to: 1.0, duration: 0.35)
            grow.timingMode = .easeOut
            sprite.run(SKAction.sequence([delay, grow]))
        }

        // Draw edges as static lines. Edges update continuously in case the user drags a node.
        drawEdgeLines(edges: visibleEdges)
    }

    private func makeCircleSprite(radius: CGFloat, fillColor: SKColor, strokeColor: SKColor, lineWidth: CGFloat) -> SKSpriteNode {
        let scale: CGFloat = 8.0
        let margin = lineWidth + 2.0
        let logicalSize = (radius + margin) * 2.0
        let pixelSize = logicalSize * scale

        let image = NSImage(size: NSSize(width: pixelSize, height: pixelSize), flipped: false) { rect in
            guard let ctx = NSGraphicsContext.current?.cgContext else { return false }
            let circleRect = CGRect(
                x: margin * scale,
                y: margin * scale,
                width: radius * 2.0 * scale,
                height: radius * 2.0 * scale
            )
            ctx.setFillColor(fillColor.cgColor)
            ctx.fillEllipse(in: circleRect)
            ctx.setStrokeColor(strokeColor.cgColor)
            ctx.setLineWidth(lineWidth * scale)
            ctx.strokeEllipse(in: circleRect)
            return true
        }

        let texture = SKTexture(image: image)
        texture.filteringMode = .linear
        let sprite = SKSpriteNode(texture: texture)
        sprite.size = CGSize(width: logicalSize, height: logicalSize)
        return sprite
    }

    private var edgeShapes: [(line: SKShapeNode, sourceId: String, targetId: String)] = []

    private func drawEdgeLines(edges: [GraphEdge]) {
        for e in edgeShapes {
            e.line.removeFromParent()
        }
        edgeShapes.removeAll()

        for edge in edges {
            guard let source = nodeSprites[edge.source], let target = nodeSprites[edge.target] else { continue }
            let line = SKShapeNode()
            line.strokeColor = SKColor.white.withAlphaComponent(0.25)
            line.lineWidth = max(0.5, CGFloat(edge.strength) * 2.0)
            line.zPosition = -1
            line.path = edgePath(from: source.position, to: target.position)
            addChild(line)
            edgeShapes.append((line, edge.source, edge.target))
        }
    }

    private func edgePath(from: CGPoint, to: CGPoint) -> CGPath {
        let path = CGMutablePath()
        path.move(to: from)
        path.addLine(to: to)
        return path
    }

    /// Update only the edges touching moved nodes, in place. Rebuilding every
    /// edge node per drag frame made dragging stutter badly.
    private func updateEdges(for movedIds: Set<String>) {
        guard !movedIds.isEmpty else { return }
        for e in edgeShapes where movedIds.contains(e.sourceId) || movedIds.contains(e.targetId) {
            guard let source = nodeSprites[e.sourceId], let target = nodeSprites[e.targetId] else { continue }
            e.line.path = edgePath(from: source.position, to: target.position)
        }
    }

    override func mouseDown(with event: NSEvent) {
        let location = event.location(in: self)
        let tapped = nodes(at: location).first { $0.userData?["node"] != nil || $0.parent?.userData?["node"] != nil }
        if let sprite = tapped as? SKSpriteNode ?? tapped?.parent as? SKSpriteNode {
            isDraggingNode = true
            draggedNode = sprite
            dragStartLocation = location
            return
        }
        isPanning = true
        lastPanLocation = location
    }

    override func mouseDragged(with event: NSEvent) {
        let location = event.location(in: self)
        if isDraggingNode, let node = draggedNode {
            let delta = CGPoint(x: location.x - node.position.x, y: location.y - node.position.y)
            node.position = location
            draggedNodeId = spriteId(node)
            retargetChildren(of: node, delta: delta)
            updateEdges(for: [spriteId(node)])
            return
        }
        guard isPanning else { return }
        let delta = CGPoint(x: location.x - lastPanLocation.x, y: location.y - lastPanLocation.y)
        cameraNode.position.x -= delta.x
        cameraNode.position.y -= delta.y
        lastPanLocation = location
    }

    /// Dragging a project or cluster node retargets its whole group; update()
    /// eases children toward the targets so the group follows with a smooth
    /// spring instead of snapping rigidly. Returns retargeted child ids.
    @discardableResult
    private func retargetChildren(of sprite: SKSpriteNode, delta: CGPoint) -> Set<String> {
        var movedIds: Set<String> = []
        guard delta.x != 0 || delta.y != 0,
              let graphNode = sprite.userData?["node"] as? GraphNode else { return movedIds }
        let childIds: [String]
        switch graphNode.type {
        case "project":
            // Node id is "project:<name>"; children carry meta.project = <name>.
            let projectName = String(graphNode.id.dropFirst("project:".count))
            childIds = nodeSprites.keys.filter { id in
                guard id != sprite.name,
                      let childNode = nodeSprites[id]?.userData?["node"] as? GraphNode else { return false }
                return childNode.meta?["project"]?.value as? String == projectName
            }
        case "cluster":
            // Node id is "cluster:<project>:<id>"; attached facts carry meta.cluster_id.
            guard let clusterId = graphNode.meta?["cluster_id"]?.value as? Int else { return movedIds }
            childIds = nodeSprites.keys.filter { id in
                guard id != sprite.name,
                      let childNode = nodeSprites[id]?.userData?["node"] as? GraphNode else { return false }
                return childNode.meta?["cluster_id"]?.value as? Int == clusterId
            }
        default:
            return movedIds
        }
        for id in childIds {
            guard let child = nodeSprites[id] else { continue }
            let current = childTargets[id] ?? child.position
            childTargets[id] = CGPoint(x: current.x + delta.x, y: current.y + delta.y)
            movedIds.insert(id)
        }
        return movedIds
    }

    private func spriteId(_ sprite: SKSpriteNode) -> String {
        sprite.name ?? ""
    }

    override func mouseUp(with event: NSEvent) {
        if isDraggingNode, let node = draggedNode {
            let location = event.location(in: self)
            // Treat it as a tap if the node barely moved; otherwise it was a drag.
            let dragDistance = hypot(location.x - dragStartLocation.x, location.y - dragStartLocation.y)
            if dragDistance < 5, let graphNode = node.userData?["node"] as? GraphNode {
                nodeTapped?(graphNode)
            }
        }
        isDraggingNode = false
        draggedNode = nil
        draggedNodeId = nil
        isPanning = false
    }

    override func mouseMoved(with event: NSEvent) {
        let location = event.location(in: self)
        // update() reads this every frame to decide which labels to show.
        hoveredNodeId = spriteAt(location)?.name
    }

    private func spriteAt(_ location: CGPoint) -> SKSpriteNode? {
        let tapped = nodes(at: location).first { $0.userData?["node"] != nil || $0.parent?.userData?["node"] != nil }
        return tapped as? SKSpriteNode ?? tapped?.parent as? SKSpriteNode
    }

    override func scrollWheel(with event: NSEvent) {
        logInput("scrollWheel deltaY=\(event.scrollingDeltaY)")
        guard event.scrollingDeltaY != 0 else { return }
        // Camera scale is inverse: scroll up = zoom in = lower scale.
        if event.scrollingDeltaY > 0 {
            applyZoom(factor: 0.962)
        } else {
            applyZoom(factor: 1.04)
        }
    }

    override func magnify(with event: NSEvent) {
        logInput("magnify mag=\(event.magnification)")
        // Pinch out (positive magnification) = zoom in = lower camera scale.
        let zoomFactor = max(0.5, 1.0 - (event.magnification * 0.4))
        applyZoom(factor: zoomFactor)
    }

    func logInput(_ message: String) {
        let logURL = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/Acrux/kg_input.log")
        try? FileManager.default.createDirectory(at: logURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        let entry = "\(Date()): \(message)\n"
        if let data = entry.data(using: .utf8) {
            if FileManager.default.fileExists(atPath: logURL.path),
               let handle = try? FileHandle(forWritingTo: logURL) {
                handle.seekToEndOfFile()
                handle.write(data)
                handle.closeFile()
            } else {
                try? data.write(to: logURL)
            }
        }
    }

    private func applyZoom(factor: CGFloat) {
        // Locked zoom range (camera scale is inverse): 0.15 = ~6.6x zoomed in,
        // 2.2 = a bit over 2x farther out than a perfect fit.
        let newScale = max(0.15, min(2.2, cameraNode.xScale * factor))
        cameraNode.setScale(newScale)
    }

    func fitToGraph(animated: Bool) {
        let positions = nodeSprites.values.map { $0.position }
        logInput("fitToGraph nodes=\(positions.count) size=\(size.width)x\(size.height)")
        guard !positions.isEmpty else { return }

        var minX = positions[0].x
        var maxX = positions[0].x
        var minY = positions[0].y
        var maxY = positions[0].y
        for p in positions {
            minX = min(minX, p.x)
            maxX = max(maxX, p.x)
            minY = min(minY, p.y)
            maxY = max(maxY, p.y)
        }

        let padding: CGFloat = 140
        let graphWidth = max(1, maxX - minX + padding * 2)
        let graphHeight = max(1, maxY - minY + padding * 2)
        // SpriteKit camera scale is inverse: visible world = view size * scale.
        // To fit the graph, the scale must be graph/view (not view/graph).
        let targetScale = min(2.5, max(0.3, max(graphWidth / size.width, graphHeight / size.height)))
        let centerX = (minX + maxX) / 2
        let centerY = (minY + maxY) / 2

        hasCompletedInitialFit = true

        logInput("fitToGraph bounds [\(Int(minX)),\(Int(minY))-\(Int(maxX)),\(Int(maxY))] targetScale=\(targetScale) center=(\(Int(centerX)),\(Int(centerY)))")

        if animated {
            let move = SKAction.move(to: CGPoint(x: centerX, y: centerY), duration: 0.35)
            move.timingMode = .easeInEaseOut
            let scale = SKAction.scale(to: targetScale, duration: 0.35)
            scale.timingMode = .easeInEaseOut
            cameraNode.run(SKAction.group([move, scale]))
        } else {
            cameraNode.position = CGPoint(x: centerX, y: centerY)
            cameraNode.setScale(targetScale)
        }
    }
}

private func validSpriteKitFontName() -> String {
    // SpriteKit needs a real PostScript font name. SFPro-Medium does not exist.
    // Try common system font names and fall back to a guaranteed font.
    let candidates = ["SFProText-Medium", "SFProDisplay-Medium", ".AppleSystemUIFontMedium", "HelveticaNeue-Medium"]
    for name in candidates {
        if NSFont(name: name, size: 12) != nil {
            return name
        }
    }
    return "Helvetica"
}

private func truncatedLabel(_ text: String, maxChars: Int) -> String {
    // Keep labels short enough that they do not spill far beyond the node circle.
    let limit = max(6, maxChars)
    if text.count <= limit { return text }
    let end = text.index(text.startIndex, offsetBy: limit - 1)
    return String(text[..<end]) + "…"
}

// MARK: - Notifications

extension Notification.Name {
    static let zoomKnowledgeGraphIn = Notification.Name("zoomKnowledgeGraphIn")
    static let zoomKnowledgeGraphOut = Notification.Name("zoomKnowledgeGraphOut")
}

// MARK: - Helpers

private extension Color {
    init?(hex: String) {
        var hexSanitized = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        hexSanitized.removeAll { $0 == "#" }
        guard hexSanitized.count == 6, let int = Int(hexSanitized, radix: 16) else { return nil }
        let r = Double((int >> 16) & 0xFF) / 255.0
        let g = Double((int >> 8) & 0xFF) / 255.0
        let b = Double(int & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b)
    }
}

private extension SKColor {
    convenience init?(hex: String) {
        var hexSanitized = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        hexSanitized.removeAll { $0 == "#" }
        guard hexSanitized.count == 6, let int = Int(hexSanitized, radix: 16) else { return nil }
        let r = CGFloat((int >> 16) & 0xFF) / 255.0
        let g = CGFloat((int >> 8) & 0xFF) / 255.0
        let b = CGFloat(int & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b, alpha: 1.0)
    }
}
