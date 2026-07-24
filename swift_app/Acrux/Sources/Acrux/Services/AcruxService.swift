import Foundation
import Combine

@MainActor
final class ChatSession {
    let chatId: UUID
    var chat: Chat
    var task: URLSessionWebSocketTask?
    var isGenerating: Bool = false
    var lastMessageAt: Date = Date()
    var generationTimeoutTimer: Timer?
    var pendingToolCalls: [ToolCall] = []
    var pendingCheckpoint: MessageCheckpoint?

    init(chat: Chat) {
        self.chat = chat
        self.chatId = chat.id
    }
}

@MainActor
final class AcruxService: ObservableObject {
    @Published var status: AcruxStatus?
    @Published var models: [OllamaModel] = []
    @Published var isConnected = false
    @Published var isBackendRunning = false
    @Published var userStoppedBackend = false
    @Published var isTogglingBackend = false
    @Published var sessions: [UUID: ChatSession] = [:]
    @Published var activeChatId: UUID?
    /// Set by views that want the Memory tab to open a specific fact tree
    /// (keys: "id", "project"); consumed and cleared by MemoryInspectorView.
    @Published var pendingFactTree: [String: String]?
    @Published var generatingChatIds: Set<UUID> = []

    weak var chatStore: ChatStore?

    var activeSession: ChatSession? { activeChatId.flatMap { sessions[$0] } }

    func isGenerating(chatId: UUID) -> Bool { sessions[chatId]?.isGenerating ?? false }

    private let process = BackendProcess()
    private var processCancellable: AnyCancellable?
    private var decoder: JSONDecoder {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        d.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let string = try container.decode(String.self)

            let withFractions = ISO8601DateFormatter()
            withFractions.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = withFractions.date(from: string) { return date }

            let withoutFractions = ISO8601DateFormatter()
            withoutFractions.formatOptions = [.withInternetDateTime]
            if let date = withoutFractions.date(from: string) { return date }

            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Invalid ISO8601 date: \(string)")
        }
        return d
    }

    private var encoder: JSONEncoder {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        e.dateEncodingStrategy = .iso8601
        return e
    }

    init() {
        processCancellable = process.$isRunning
            .receive(on: DispatchQueue.main)
            .sink { [weak self] running in
                self?.isBackendRunning = running
                if running {
                    Task { await self?.fetchModels() }
                }
            }
    }

    func startBackend() {
        guard !isTogglingBackend else { return }
        userStoppedBackend = false
        guard PermissionManager.shared.ensureAccess() else { return }
        isTogglingBackend = true
        process.start()
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { [weak self] in
            guard let self else { return }
            self.isTogglingBackend = false
            if !self.process.isRunning {
                self.isBackendRunning = false
                self.isConnected = false
            }
        }
    }

    func stopBackend() {
        guard !isTogglingBackend else { return }
        userStoppedBackend = true
        isTogglingBackend = true
        process.stop()
        isConnected = false
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { [weak self] in
            guard let self else { return }
            self.isTogglingBackend = false
            self.isBackendRunning = self.process.isRunning
        }
    }

    func fetchStatus() async {
        guard let url = URL(string: "\(Constants.backendURL)/api/acrux/status") else { return }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            status = try decoder.decode(AcruxStatus.self, from: data)
            isConnected = true
            isBackendRunning = status?.running ?? false
        } catch {
            isConnected = false
            isBackendRunning = false
            status = nil
        }
    }

    func fetchModels() async {
        guard let url = URL(string: "\(Constants.backendURL)/api/models") else { return }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let response = try decoder.decode(ModelsResponse.self, from: data)
            models = response.models
                .filter { !$0.name.lowercased().contains("embed") && !$0.name.lowercased().contains("bge") }
                .sorted { modelPriority($0.name) > modelPriority($1.name) }
        } catch {
            models = []
        }
    }

    private func modelPriority(_ name: String) -> Int {
        let lower = name.lowercased()
        if lower.contains("qwen3") { return 100 }
        if lower.contains("qwen2.5") { return 90 }
        if lower.contains("qwen2") { return 80 }
        if lower.contains("llama3") { return 70 }
        if lower.contains("mistral") || lower.contains("mixtral") { return 60 }
        if lower.contains("llava") || lower.contains("vision") { return -10 }
        return 0
    }

    func fetchKnowledgeSummary() async throws -> String {
        guard let url = URL(string: "\(Constants.backendURL)/api/acrux/knowledge") else { throw URLError(.badURL) }
        let (data, _) = try await URLSession.shared.data(from: url)
        let response = try decoder.decode(KnowledgeResponse.self, from: data)
        return response.summary
    }

    func searchMemory(
        query: String,
        project: String = "",
        tags: [String] = [],
        limit: Int = 20,
        factType: String? = nil,
        since: Date? = nil,
        until: Date? = nil
    ) async -> [MemorySearchResult] {
        var components = URLComponents(string: "\(Constants.backendURL)/api/search")!
        var queryItems = [
            URLQueryItem(name: "project", value: project),
            URLQueryItem(name: "query", value: query),
            URLQueryItem(name: "limit", value: String(limit))
        ]
        if !tags.isEmpty {
            queryItems.append(URLQueryItem(name: "tags", value: tags.joined(separator: ",")))
        }
        if let factType {
            queryItems.append(URLQueryItem(name: "fact_type", value: factType))
        }
        if let since {
            queryItems.append(URLQueryItem(name: "since", value: ISO8601DateFormatter().string(from: since)))
        }
        if let until {
            queryItems.append(URLQueryItem(name: "until", value: ISO8601DateFormatter().string(from: until)))
        }
        components.queryItems = queryItems
        guard let url = components.url else { return [] }
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 404 {
                return []
            }
            return try decoder.decode([MemorySearchResult].self, from: data)
        } catch {
            return []
        }
    }

    // MARK: - Acrux Control

    func reverifyFacts() async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/acrux/reverify") else { return false }
        do {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Memory Inspector

    func fetchMemories(endpoint: String, query: String = "", tags: [String] = [], project: String = "global") async throws -> [MemoryItem] {
        try await fetchMemories(endpoint: endpoint, query: query, tags: tags, project: project, factType: nil, clusterId: nil, since: nil, until: nil)
    }

    func fetchMemories(
        endpoint: String,
        query: String = "",
        tags: [String] = [],
        project: String = "global",
        factType: String? = nil,
        clusterId: String? = nil,
        since: Date? = nil,
        until: Date? = nil
    ) async throws -> [MemoryItem] {
        var components = URLComponents(string: "\(Constants.backendURL)/api/memories/\(endpoint)")!
        var queryItems: [URLQueryItem] = [URLQueryItem(name: "project", value: project)]
        if !query.isEmpty {
            queryItems.append(URLQueryItem(name: "query", value: query))
        }
        if !tags.isEmpty {
            queryItems.append(URLQueryItem(name: "tags", value: tags.joined(separator: ",")))
        }
        if let factType {
            queryItems.append(URLQueryItem(name: "fact_type", value: factType))
        }
        if let clusterId {
            queryItems.append(URLQueryItem(name: "cluster_id", value: clusterId))
        }
        if let since {
            queryItems.append(URLQueryItem(name: "since", value: ISO8601DateFormatter().string(from: since)))
        }
        if let until {
            queryItems.append(URLQueryItem(name: "until", value: ISO8601DateFormatter().string(from: until)))
        }
        components.queryItems = queryItems
        guard let url = components.url else { throw URLError(.badURL) }
        let (data, response) = try await URLSession.shared.data(from: url)
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode >= 400 {
            throw URLError(.badServerResponse)
        }
        let wrapper = try decoder.decode(MemoryListResponse.self, from: data)
        switch endpoint {
        case "facts": return wrapper.facts ?? []
        case "episodes": return wrapper.episodes ?? []
        case "skills": return wrapper.skills ?? []
        default: return []
        }
    }

    func deleteMemory(id: String, endpoint: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/memories/\(endpoint)/\(id)") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func updateFact(id: String, content: String, tags: [String]) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/memories/facts/\(id)") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = FactUpdateRequest(content: content, tags: tags)
        request.httpBody = try? encoder.encode(body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Fact hierarchy

    func fetchFactTree(id: String, project: String = "global") async -> FactNode? {
        var components = URLComponents(string: "\(Constants.backendURL)/api/memories/facts/\(id)/tree")!
        components.queryItems = [URLQueryItem(name: "project", value: project)]
        guard let url = components.url else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode(FactTreeResponse.self, from: data).tree.asFactNode()
        } catch {
            return nil
        }
    }

    func createChildFact(parentId: String, content: String, tags: [String] = [], project: String = "global") async -> Bool {
        var components = URLComponents(string: "\(Constants.backendURL)/api/memories/facts/\(parentId)/children")!
        components.queryItems = [URLQueryItem(name: "project", value: project)]
        guard let url = components.url else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = FactUpdateRequest(content: content, tags: tags)
        request.httpBody = try? encoder.encode(body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func linkFacts(sourceId: String, targetId: String, relationType: String = "related") async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/memories/facts/\(sourceId)/link") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = LinkFactsRequest(targetId: targetId, relationType: relationType)
        request.httpBody = try? encoder.encode(body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Fact versions

    func fetchFactVersions(id: String) async -> [FactVersion] {
        guard let url = URL(string: "\(Constants.backendURL)/api/memories/facts/\(id)/versions") else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([FactVersion].self, from: data)
        } catch {
            return []
        }
    }

    func restoreFactVersion(factId: String, versionId: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/memories/facts/\(factId)/versions/\(versionId)/restore") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Clusters

    func triggerClustering(project: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/acrux/cluster") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["project": project]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func fetchClusters(project: String) async -> [Cluster] {
        var components = URLComponents(string: "\(Constants.backendURL)/api/acrux/clusters")!
        components.queryItems = [URLQueryItem(name: "project", value: project)]
        guard let url = components.url else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([Cluster].self, from: data)
        } catch {
            return []
        }
    }

    // MARK: - Inheritance

    func fetchInheritance(project: String) async -> [InheritanceLayer] {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/inheritance") else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([InheritanceLayer].self, from: data)
        } catch {
            return []
        }
    }

    func addInheritance(project: String, baseProject: String, layerOrder: Int = 0) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/inheritance") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = AddInheritanceRequest(baseProject: baseProject, layerOrder: layerOrder)
        request.httpBody = try? encoder.encode(body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func removeInheritance(project: String, baseProject: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/inheritance/\(baseProject.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? baseProject)") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func fetchEffectiveFacts(project: String) async -> [MemoryItem] {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/effective-facts") else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([MemoryItem].self, from: data)
        } catch {
            return []
        }
    }

    // MARK: - Timeline

    func fetchTimeline(project: String = "", since: Date? = nil, until: Date? = nil) async -> [TimelineEvent] {
        var components = URLComponents(string: "\(Constants.backendURL)/api/acrux/timeline")!
        var queryItems: [URLQueryItem] = [URLQueryItem(name: "project", value: project)]
        if let since {
            queryItems.append(URLQueryItem(name: "since", value: ISO8601DateFormatter().string(from: since)))
        }
        if let until {
            queryItems.append(URLQueryItem(name: "until", value: ISO8601DateFormatter().string(from: until)))
        }
        components.queryItems = queryItems
        guard let url = components.url else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([TimelineEvent].self, from: data)
        } catch {
            return []
        }
    }

    // MARK: - Decay

    func recomputeDecay() async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/acrux/decay") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func fetchStaleFacts(project: String = "", threshold: Double = 0.7) async -> [DecayFact] {
        var components = URLComponents(string: "\(Constants.backendURL)/api/acrux/decay")!
        components.queryItems = [
            URLQueryItem(name: "project", value: project),
            URLQueryItem(name: "threshold", value: String(threshold))
        ]
        guard let url = components.url else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([DecayFact].self, from: data)
        } catch {
            return []
        }
    }

    // MARK: - Tests

    func fetchTestResults(project: String) async -> [TestResult] {
        if project.isEmpty { return [] }
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/tests") else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([TestResult].self, from: data)
        } catch {
            return []
        }
    }

    func recordTestResult(_ test: RecordTestRequest, project: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/tests") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONEncoder().encode(test)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Dependencies

    func fetchDependencies(project: String, source: String? = nil, target: String? = nil) async -> [Dependency] {
        var components = URLComponents(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/dependencies")!
        var queryItems: [URLQueryItem] = []
        if let source {
            queryItems.append(URLQueryItem(name: "source", value: source))
        }
        if let target {
            queryItems.append(URLQueryItem(name: "target", value: target))
        }
        if !queryItems.isEmpty { components.queryItems = queryItems }
        guard let url = components.url else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([Dependency].self, from: data)
        } catch {
            return []
        }
    }

    func ingestDependencies(project: String, dependencies: [DependencyInput]) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/dependencies") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = IngestDependenciesRequest(dependencies: dependencies)
        request.httpBody = try? encoder.encode(body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Reviews

    func fetchReviews(project: String, filePath: String? = nil) async -> [CodeReview] {
        var components = URLComponents(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/reviews")!
        if let filePath {
            components.queryItems = [URLQueryItem(name: "file_path", value: filePath)]
        }
        guard let url = components.url else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([CodeReview].self, from: data)
        } catch {
            return []
        }
    }

    func addReview(project: String, request: AddReviewRequest) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/reviews") else { return false }
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try? encoder.encode(request)
        do {
            let (_, response) = try await URLSession.shared.data(for: urlRequest)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - File summaries

    func fetchFileSummaries(project: String) async -> [FileSummary] {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/file-summaries") else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([FileSummary].self, from: data)
        } catch {
            return []
        }
    }

    func summarizeFile(project: String, path: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/file-summaries") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = SummarizeFileRequest(path: path)
        request.httpBody = try? encoder.encode(body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Import / Export

    func importNotion(path: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/import/notion") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["path": path])
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func importObsidian(path: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/import/obsidian") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["path": path])
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func exportMarkdown(project: String = "", format: String = "obsidian") async -> Data? {
        var components = URLComponents(string: "\(Constants.backendURL)/api/export/markdown")!
        components.queryItems = [
            URLQueryItem(name: "project", value: project),
            URLQueryItem(name: "format", value: format)
        ]
        guard let url = components.url else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return data
        } catch {
            return nil
        }
    }

    // MARK: - Watcher

    func setWatcher(project: String, running: Bool) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/watcher/\(running ? "start" : "stop")") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func fetchWatcherStatus(project: String) async -> WatcherStatus? {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/watcher/status") else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode(WatcherStatus.self, from: data)
        } catch {
            return nil
        }
    }

    // MARK: - Health

    func fetchHealthChecks() async -> [HealthCheck] {
        guard let url = URL(string: "\(Constants.backendURL)/api/acrux/health") else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let wrapper = try decoder.decode(HealthCheckResponse.self, from: data)
            return wrapper.checks
        } catch {
            return []
        }
    }

    func runHealthChecks() async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/acrux/health/run") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Checksums

    func fetchChecksums() async -> [ChecksumStatus] {
        guard let url = URL(string: "\(Constants.backendURL)/api/acrux/checksums") else { return [] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode([ChecksumStatus].self, from: data)
        } catch {
            return []
        }
    }

    // MARK: - Rollback

    func fetchRollbackSuggestion(project: String, afterCommand: String? = nil) async -> RollbackSuggestion? {
        var components = URLComponents(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/rollback-suggestion")!
        if let afterCommand {
            components.queryItems = [URLQueryItem(name: "after_command", value: afterCommand)]
        }
        guard let url = components.url else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode(RollbackSuggestion.self, from: data)
        } catch {
            return nil
        }
    }

    // MARK: - Episode Replay

    func startReplay(sessionId: String, workspace: String? = nil, force: Bool = false, autoApprove: Bool = false) async -> ReplayStatus? {
        guard let url = URL(string: "\(Constants.backendURL)/api/episodes/\(sessionId)/replay") else { return nil }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ReplayStartRequest(workspace: workspace, force: force, autoApprove: autoApprove)
        request.httpBody = try? encoder.encode(body)
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else { return nil }
            return try decoder.decode(ReplayStatus.self, from: data)
        } catch {
            return nil
        }
    }

    func fetchReplayStatus(sessionId: String) async -> ReplayStatus? {
        guard let url = URL(string: "\(Constants.backendURL)/api/episodes/\(sessionId)/replay/status") else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode(ReplayStatus.self, from: data)
        } catch {
            return nil
        }
    }

    func stepReplay(sessionId: String, autoApprove: Bool? = nil) async -> ReplayStatus? {
        guard let url = URL(string: "\(Constants.backendURL)/api/episodes/\(sessionId)/replay/step") else { return nil }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ReplayStepRequest(autoApprove: autoApprove)
        request.httpBody = try? encoder.encode(body)
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else { return nil }
            return try decoder.decode(ReplayStatus.self, from: data)
        } catch {
            return nil
        }
    }

    func abortReplay(sessionId: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/episodes/\(sessionId)/replay/abort") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func restoreReplayCommit(sessionId: String) async -> ReplayStatus? {
        guard let url = URL(string: "\(Constants.backendURL)/api/episodes/\(sessionId)/replay/restore") else { return nil }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else { return nil }
            return try decoder.decode(ReplayStatus.self, from: data)
        } catch {
            return nil
        }
    }

    // MARK: - Knowledge Graph

    func fetchGraph(project: String, maxNodes: Int = 200) async throws -> GraphResponse? {
        let urlString: String
        if project.isEmpty {
            urlString = "\(Constants.backendURL)/api/acrux/graph?max_nodes=\(maxNodes)"
        } else {
            urlString = "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/graph?max_nodes=\(maxNodes)"
        }
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        let (data, response) = try await URLSession.shared.data(from: url)
        let statusCode = (response as? HTTPURLResponse)?.statusCode ?? 0
        let headers = (response as? HTTPURLResponse)?.allHeaderFields as? [String: Any] ?? [:]
        if statusCode >= 400 {
            throw URLError(.badServerResponse)
        }
        do {
            return try decoder.decode(GraphResponse.self, from: data)
        } catch {
            let logsDir = FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("Library/Logs/Acrux")
            try? FileManager.default.createDirectory(at: logsDir, withIntermediateDirectories: true)
            let rawURL = logsDir.appendingPathComponent("kg_raw_response.json")
            let reportURL = logsDir.appendingPathComponent("kg_decode_error.log")
            try? data.write(to: rawURL)
            let report = """
            URL: \(urlString)
            Status: \(statusCode)
            Headers: \(headers)
            Error: \(error)
            Data bytes: \(data.count)
            Response preview: \(String(data: data.prefix(2000), encoding: .utf8) ?? "(not utf8)")
            """
            try? report.write(to: reportURL, atomically: true, encoding: .utf8)
            throw error
        }
    }

    // MARK: - System prompt

    func fetchSystemPrompt(project: String) async -> SystemPrompt? {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/system-prompt") else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            return try decoder.decode(SystemPrompt.self, from: data)
        } catch {
            return nil
        }
    }

    func updateSystemPrompt(project: String, promptText: String) async -> Bool {
        guard let url = URL(string: "\(Constants.backendURL)/api/projects/\(project.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? project)/system-prompt") else { return false }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = UpdateSystemPromptRequest(promptText: promptText)
        request.httpBody = try? encoder.encode(body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Skill Suggestions

    func suggestSkills(for message: String) async -> [SkillSuggestion] {
        guard let url = URL(string: "\(Constants.backendURL)/api/skills/suggest") else { return [] }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let payload = ["message": message]
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else { return [] }
            return try decoder.decode([SkillSuggestion].self, from: data)
        } catch {
            return []
        }
    }

    // MARK: - Chat

    func connect(to chat: Chat) {
        activeChatId = chat.id
        if let existing = sessions[chat.id] {
            if existing.task?.state != .running {
                existing.task?.cancel()
                guard let url = URL(string: "\(Constants.wsURL)/ws/chat/\(chat.id.uuidString)") else { return }
                existing.task = URLSession.shared.webSocketTask(with: url)
                existing.task?.resume()
                receive(for: existing)
            }
            return
        }
        let session = ChatSession(chat: chat)
        sessions[chat.id] = session
        guard let url = URL(string: "\(Constants.wsURL)/ws/chat/\(chat.id.uuidString)") else { return }
        session.task = URLSession.shared.webSocketTask(with: url)
        session.task?.resume()
        receive(for: session)
    }

    func disconnect(from chat: Chat) {
        guard let session = sessions[chat.id] else { return }
        session.generationTimeoutTimer?.invalidate()
        session.task?.cancel(with: .normalClosure, reason: nil)
        sessions.removeValue(forKey: chat.id)
        generatingChatIds.remove(chat.id)
        if activeChatId == chat.id {
            activeChatId = sessions.keys.first
        }
    }

    func closeChat(_ chat: Chat) {
        disconnect(from: chat)
    }

    func send(_ text: String, to chat: Chat) {
        var session = sessions[chat.id]
        if session == nil {
            connect(to: chat)
            session = sessions[chat.id]
        }
        guard let session else { return }

        var updatedChat = chatStore?.chat(id: chat.id) ?? chat
        let userMessage = Message(id: UUID(), role: "user", content: text, reasoning: nil, toolCalls: nil, toolResults: nil, timestamp: Date(), pinned: nil, checkpoint: nil)
        updatedChat.messages.append(userMessage)
        updatedChat.updatedAt = Date()
        if updatedChat.title == "New task" {
            updatedChat.title = String(text.prefix(40)) + (text.count > 40 ? "..." : "")
        }
        chatStore?.save(updatedChat)
        session.chat = updatedChat
        sessions[chat.id] = session

        session.isGenerating = true
        session.lastMessageAt = Date()
        if !generatingChatIds.contains(chat.id) {
            generatingChatIds.insert(chat.id)
        }
        resetGenerationTimeout(for: session)
        sessions[chat.id] = session

        let payload: [String: Any] = [
            "type": "start",
            "message": text,
            "model": updatedChat.model,
            "workspace": updatedChat.workspace,
            "auto_accept": updatedChat.autoAccept,
            "allowed_tools": updatedChat.allowedTools,
            "use_memory": updatedChat.useMemory,
            "loop_mode": updatedChat.loopMode,
            "checkpoint_interval": updatedChat.checkpointInterval
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let string = String(data: data, encoding: .utf8) else { return }
        session.task?.send(.string(string)) { _ in }
    }

    func stop(chat: Chat) {
        guard let session = sessions[chat.id] else { return }
        let payload: [String: Any] = ["type": "stop"]
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let string = String(data: data, encoding: .utf8) else { return }
        session.task?.send(.string(string)) { _ in }
    }

    func approveTool(id: String, approve: Bool, in chat: Chat? = nil) {
        let chatId = chat?.id ?? activeChatId
        guard let session = chatId.flatMap({ sessions[$0] }) else { return }
        let payload: [String: Any] = [
            "type": approve ? "approve_tool" : "deny_tool",
            "id": id
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let string = String(data: data, encoding: .utf8) else { return }
        session.task?.send(.string(string)) { _ in }
        session.pendingToolCalls.removeAll { $0.id == id }
        sessions[session.chatId] = session
    }

    func resolveCheckpoint(action: String, in chat: Chat? = nil) {
        let chatId = chat?.id ?? activeChatId
        guard let session = chatId.flatMap({ sessions[$0] }) else { return }
        let payload: [String: Any] = ["type": "checkpoint_response", "action": action]
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let string = String(data: data, encoding: .utf8) else { return }
        session.task?.send(.string(string)) { _ in }
        session.pendingCheckpoint = nil
        sessions[session.chatId] = session
    }

    private func receive(for session: ChatSession) {
        session.task?.receive { [weak self, weak session] result in
            guard let self, let session else { return }
            switch result {
            case .success(let message):
                Task { @MainActor in
                    self.handle(message, session: session)
                    self.receive(for: session)
                }
            case .failure:
                Task { @MainActor in
                    session.isGenerating = false
                    self.generatingChatIds.remove(session.chatId)
                    self.sessions[session.chatId] = session
                }
            }
        }
    }

    private func handle(_ message: URLSessionWebSocketTask.Message, session: ChatSession) {
        let data: Data
        switch message {
        case .string(let text):
            guard let d = text.data(using: .utf8) else { return }
            data = d
        case .data(let d):
            data = d
        @unknown default:
            return
        }

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return }

        session.lastMessageAt = Date()
        resetGenerationTimeout(for: session)

        switch type {
        case "reasoning":
            if let content = json["content"] as? String {
                appendReasoning(content, session: session)
            }
        case "assistant_start":
            session.isGenerating = true
            if !generatingChatIds.contains(session.chatId) {
                generatingChatIds.insert(session.chatId)
            }
            ensureAssistantMessage(session: session)
        case "content":
            if let content = json["content"] as? String {
                appendContent(content, session: session)
            }
        case "tool_call":
            if let id = json["id"] as? String,
               let name = json["name"] as? String,
               let args = json["arguments"] as? [String: Any] {
                let toolCall = ToolCall(id: id, name: name, arguments: args.mapValues(AnyCodable.init))
                session.pendingToolCalls.append(toolCall)
                appendToolCall(toolCall, session: session)
                // Read the freshest autoAccept value — the header toggle saves
                // to the store, but session.chat may be stale.
                let freshAutoAccept = chatStore?.chat(id: session.chatId)?.autoAccept ?? session.chat.autoAccept
                if freshAutoAccept {
                    approveTool(id: id, approve: true, in: session.chat)
                }
            }
        case "tool_result":
            if let id = json["id"] as? String,
               let output = json["output"] as? String {
                appendToolResult(id: id, output: output, session: session)
                session.pendingToolCalls.removeAll { $0.id == id }
            }
        case "checkpoint":
            if let checkpoint = MessageCheckpoint(from: json) {
                session.pendingCheckpoint = checkpoint
            }
        case "done":
            finalizeGeneration(for: session)
        case "stopped":
            finalizeGeneration(for: session, stopped: true)
        case "error":
            if let msg = json["message"] as? String {
                finalizeGeneration(for: session, errorMessage: "Error: \(msg)")
            }
        default:
            break
        }

        sessions[session.chatId] = session
    }

    private func finalizeGeneration(for session: ChatSession, stopped: Bool = false, errorMessage: String? = nil) {
        session.isGenerating = false
        session.generationTimeoutTimer?.invalidate()
        session.generationTimeoutTimer = nil
        session.pendingToolCalls = []
        session.pendingCheckpoint = nil
        if let errorMessage {
            appendContent(errorMessage, session: session)
        } else if stopped {
            appendContent("Generation stopped.", session: session)
        }
        chatStore?.save(session.chat)
        generatingChatIds.remove(session.chatId)
        sessions[session.chatId] = session
    }

    private func resetGenerationTimeout(for session: ChatSession) {
        session.generationTimeoutTimer?.invalidate()
        guard session.isGenerating else { return }
        // Tool-enabled turns are non-streaming on the backend, so long
        // generations are silent for minutes. Use a generous window, and
        // never time out while the user is mid-approval on a tool call.
        let silenceLimit: TimeInterval = 600
        session.generationTimeoutTimer = Timer.scheduledTimer(withTimeInterval: silenceLimit, repeats: false) { [weak self, weak session] _ in
            guard let self, let session else { return }
            Task { @MainActor in
                guard session.isGenerating else { return }
                if !session.pendingToolCalls.isEmpty || session.pendingCheckpoint != nil {
                    self.resetGenerationTimeout(for: session)
                    return
                }
                let elapsed = Date().timeIntervalSince(session.lastMessageAt)
                guard elapsed >= silenceLimit else {
                    self.resetGenerationTimeout(for: session)
                    return
                }
                self.finalizeGeneration(for: session, errorMessage: "Error: generation timed out.")
            }
        }
    }

    private func appendReasoning(_ text: String, session: ChatSession) {
        if let last = session.chat.messages.indices.last, session.chat.messages[last].role == "assistant" {
            session.chat.messages[last].reasoning = (session.chat.messages[last].reasoning ?? "") + text
        } else {
            let msg = Message(id: UUID(), role: "assistant", content: "", reasoning: text, toolCalls: nil, toolResults: nil, timestamp: Date())
            session.chat.messages.append(msg)
        }
        chatStore?.save(session.chat)
        sessions[session.chatId] = session
    }

    private func ensureAssistantMessage(session: ChatSession) {
        if session.chat.messages.isEmpty || session.chat.messages.last?.role != "assistant" {
            let msg = Message(id: UUID(), role: "assistant", content: "", reasoning: nil, toolCalls: nil, toolResults: nil, timestamp: Date())
            session.chat.messages.append(msg)
        }
    }

    private func appendContent(_ text: String, session: ChatSession) {
        ensureAssistantMessage(session: session)
        if let last = session.chat.messages.indices.last {
            session.chat.messages[last].content += text
        }
        chatStore?.save(session.chat)
        sessions[session.chatId] = session
    }

    private func appendToolCall(_ toolCall: ToolCall, session: ChatSession) {
        if session.chat.messages.isEmpty || session.chat.messages.last?.role != "assistant" {
            let msg = Message(id: UUID(), role: "assistant", content: "", reasoning: nil, toolCalls: [toolCall], toolResults: nil, timestamp: Date())
            session.chat.messages.append(msg)
        } else {
            session.chat.messages[session.chat.messages.count - 1].toolCalls = (session.chat.messages[session.chat.messages.count - 1].toolCalls ?? []) + [toolCall]
        }
        chatStore?.save(session.chat)
        sessions[session.chatId] = session
    }

    private func appendToolResult(id: String, output: String, session: ChatSession) {
        let result = ToolResult(id: id, output: output)
        if let last = session.chat.messages.indices.last {
            session.chat.messages[last].toolResults = (session.chat.messages[last].toolResults ?? []) + [result]
        }
        chatStore?.save(session.chat)
        sessions[session.chatId] = session
    }
}

private struct MemoryListResponse: Codable {
    let project: String?
    let count: Int?
    let facts: [MemoryItem]?
    let episodes: [MemoryItem]?
    let skills: [MemoryItem]?
}

private struct ModelsResponse: Codable {
    let models: [OllamaModel]
}

private struct KnowledgeResponse: Codable {
    let summary: String
}

struct MemorySearchResult: Codable, Identifiable {
    let id: String
    let content: String
    let score: Double?
    let project: String?
    let source: String?
    let confidence: Double?
    let stale: Bool?
    let tags: [String]?
    let gitBranch: String?
    let gitCommit: String?

    var gitLabel: String? {
        guard let branch = gitBranch, !branch.isEmpty else { return nil }
        let shortCommit = gitCommit?.prefix(7) ?? ""
        return "\(branch)@\(shortCommit)"
    }
}

private extension MessageCheckpoint {
    init?(from json: [String: Any]) {
        guard let turn = json["turn"] as? Int else { return nil }
        self.turn = turn
        self.toolName = json["tool_name"] as? String
        self.message = json["message"] as? String
    }
}
