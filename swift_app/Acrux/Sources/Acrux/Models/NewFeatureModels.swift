import Foundation

// MARK: - Status extensions

struct StorageStatus: Codable {
    let storageUsedBytes: Int
    let storageLimitBytes: Int
    let storagePercent: Double
}

// MARK: - Hierarchy

struct FactNode: Identifiable, Codable {
    let id: String
    let content: String
    let factType: String?
    let confidence: Double?
    let decayScore: Double?
    let clusterId: String?
    let children: [FactNode]
}

// The /tree endpoint wraps each node as {"fact": {...}, "ancestors": [...],
// "children": [...]}, so decode through an intermediate shape and map it.
struct FactTreeResponse: Codable {
    let tree: FactTreeNode
}

struct FactTreeNode: Codable {
    let fact: FactTreeFact
    let children: [FactTreeNode]

    func asFactNode() -> FactNode {
        FactNode(
            id: String(fact.id),
            content: fact.content,
            factType: fact.factType,
            confidence: fact.confidence,
            decayScore: nil,
            clusterId: nil,
            children: children.map { $0.asFactNode() }
        )
    }
}

struct FactTreeFact: Codable {
    let id: Int
    let content: String
    let factType: String?
    let confidence: Double?
}

struct LinkFactsRequest: Codable {
    let targetId: String
    let relationType: String?
}

// MARK: - Versions

struct FactVersion: Identifiable, Codable {
    let id: String
    let factId: String
    let content: String
    let tags: [String]?
    let editedAt: Date
    let editedBy: String?
}

// MARK: - Clusters

struct Cluster: Identifiable, Codable {
    let id: String
    let project: String?
    let label: String?
    let createdAt: Date?
    let updatedAt: Date?
}

// MARK: - Inheritance

struct InheritanceLayer: Identifiable, Codable {
    let id: String
    let project: String
    let baseProject: String
    let layerOrder: Int
}

struct AddInheritanceRequest: Codable {
    let baseProject: String
    let layerOrder: Int?
}

// MARK: - Timeline

struct TimelineEvent: Identifiable, Codable {
    let id: String
    let type: String
    let content: String
    let timestamp: Date
    let project: String?
}

// MARK: - Decay

struct DecayFact: Identifiable, Codable {
    let id: String
    let content: String
    let decayScore: Double
    let lastRecalledAt: Date?
}

// MARK: - Tests

struct TestResult: Identifiable, Codable {
    let id: String
    let project: String
    let testName: String
    let filePath: String?
    let passed: Bool
    let output: String?
    let durationMs: Int?
    let rootCause: String?
    let runAt: Date
}

struct RecordTestRequest: Codable {
    let testName: String
    let filePath: String?
    let passed: Bool
    let output: String?
    let durationMs: Int?
    let rootCause: String?
    let runAt: Date?
}

// MARK: - Dependencies

struct Dependency: Identifiable, Codable {
    let id: String
    let project: String
    let sourceRef: String
    let sourceType: String
    let targetRef: String
    let targetType: String
    let dependencyType: String
    let detectedAt: Date?
}

struct IngestDependenciesRequest: Codable {
    let dependencies: [DependencyInput]
}

struct DependencyInput: Codable {
    let sourceRef: String
    let sourceType: String
    let targetRef: String
    let targetType: String
    let dependencyType: String
}

// MARK: - Reviews

struct CodeReview: Identifiable, Codable {
    let id: String
    let project: String
    let filePath: String
    let lineRange: String?
    let comment: String
    let resolution: String?
    let reviewer: String?
    let timestamp: Date?
}

struct AddReviewRequest: Codable {
    let filePath: String
    let lineRange: String?
    let comment: String
    let reviewer: String?
}

// MARK: - File summaries

struct FileSummary: Identifiable, Codable {
    let id: String
    let project: String
    let path: String
    let summary: String
    let contentHash: String?
    let lastModified: Date?
    let indexedAt: Date?
}

struct SummarizeFileRequest: Codable {
    let path: String
}

// MARK: - Watcher

struct WatcherStatus: Codable {
    let running: Bool
    let project: String?
    let watchedPaths: [String]?
}

// MARK: - Health

struct HealthCheck: Identifiable, Codable {
    let id: String
    let project: String?
    let checkType: String
    let severity: String
    let message: String
    let createdAt: Date
    let resolvedAt: Date?
}

struct HealthCheckResponse: Codable {
    let checks: [HealthCheck]
    let count: Int
}

// MARK: - Checksums

struct ChecksumStatus: Identifiable, Codable {
    let id: String
    let filePath: String
    let checksum: String
    let checkedAt: Date?
}

// MARK: - Rollback

struct RollbackSuggestion: Codable {
    let command: String?
    let description: String?
    let targetCommit: String?
    let filesToRevert: [String]?
}

// MARK: - System prompt

struct SystemPrompt: Codable {
    let project: String
    let promptText: String
    let updatedAt: Date?
}

struct UpdateSystemPromptRequest: Codable {
    let promptText: String
}

// MARK: - Search extensions

struct MemorySearchFilters: Codable {
    var factType: String?
    var since: Date?
    var until: Date?
}

// MARK: - Episode Replay

struct ReplayStatus: Codable {
    let sessionId: String
    let status: String
    let totalSteps: Int
    let currentStep: Int
    let originalAction: ReplayAction?
    let proposedAction: ReplayAction?
    let requiresApproval: Bool
    let outputPreview: String?
    let diff: String?
    let divergences: [String]?
    let warnings: [String]?
    let gitCheckoutOk: Bool?
    let newEpisodeId: String?
    let outcome: String?
    let message: String?
}

struct ReplayAction: Codable {
    let tool: String
    let target: String
    let command: String
    let result: String
    let diff: String
}

struct ReplayStartRequest: Codable {
    let workspace: String?
    let force: Bool
    let autoApprove: Bool
}

struct ReplayStepRequest: Codable {
    let autoApprove: Bool?
}

// MARK: - Knowledge Graph

struct GraphNode: Identifiable, Codable {
    let id: String
    let type: String
    let label: String
    let contentSnippet: String
    let size: Double
    let color: String
    var x: Double
    var y: Double
    let meta: [String: AnyCodable]?
}

struct GraphEdge: Identifiable, Codable {
    let source: String
    let target: String
    let type: String
    let strength: Double

    var id: String { "\(source)->\(target)" }
}

struct GraphResponse: Codable {
    let project: String
    let nodeCount: Int
    let edgeCount: Int
    let nodes: [GraphNode]
    let edges: [GraphEdge]
}
