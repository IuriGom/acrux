import Foundation

struct MemoryItem: Identifiable, Codable {
    let id: String
    var content: String
    let source: String?
    var tags: [String]
    let timestamp: Date?
    let confidence: Double?
    let stale: Bool?
    let gitBranch: String?
    let gitCommit: String?

    // New batch fields
    var factType: String?
    var parentId: String?
    var versionGroupId: String?
    var isCurrent: Bool?
    var clusterId: String?
    var inheritanceMode: String?
    var decayScore: Double?
    var lastRecalledAt: Date?
    var checksum: String?

    var gitLabel: String? {
        guard let branch = gitBranch, !branch.isEmpty else { return nil }
        let shortCommit = gitCommit?.prefix(7) ?? ""
        return "\(branch)@\(shortCommit)"
    }

    var isNegative: Bool { factType?.lowercased() == "negative" }

    enum CodingKeys: String, CodingKey {
        case id
        case sessionId = "session_id"
        case content
        case task
        case name
        case source
        case tags
        case timestamp
        case confidence
        case stale
        case gitInfo = "git_info"
        case factType = "fact_type"
        case parentId = "parent_id"
        case versionGroupId = "version_group_id"
        case isCurrent = "is_current"
        case clusterId = "cluster_id"
        case inheritanceMode = "inheritance_mode"
        case decayScore = "decay_score"
        case lastRecalledAt = "last_recalled_at"
        case checksum
    }

    init(id: String, content: String, source: String? = nil, tags: [String] = [], timestamp: Date? = nil, confidence: Double? = nil, stale: Bool? = nil, gitBranch: String? = nil, gitCommit: String? = nil, factType: String? = nil, parentId: String? = nil, versionGroupId: String? = nil, isCurrent: Bool? = nil, clusterId: String? = nil, inheritanceMode: String? = nil, decayScore: Double? = nil, lastRecalledAt: Date? = nil, checksum: String? = nil) {
        self.id = id
        self.content = content
        self.source = source
        self.tags = tags
        self.timestamp = timestamp
        self.confidence = confidence
        self.stale = stale
        self.gitBranch = gitBranch
        self.gitCommit = gitCommit
        self.factType = factType
        self.parentId = parentId
        self.versionGroupId = versionGroupId
        self.isCurrent = isCurrent
        self.clusterId = clusterId
        self.inheritanceMode = inheritanceMode
        self.decayScore = decayScore
        self.lastRecalledAt = lastRecalledAt
        self.checksum = checksum
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        // ID can be an Int (facts), String (episodes/skills), or missing (use session_id).
        if let intId = try? container.decode(Int.self, forKey: .id) {
            self.id = String(intId)
        } else if let stringId = try? container.decode(String.self, forKey: .id) {
            self.id = stringId
        } else if let sessionId = try? container.decode(String.self, forKey: .sessionId) {
            self.id = sessionId
        } else {
            self.id = UUID().uuidString
        }

        // Content can be `content` (facts), `task` (episodes), or `name` (skills).
        if let content = try? container.decode(String.self, forKey: .content), !content.isEmpty {
            self.content = content
        } else if let task = try? container.decode(String.self, forKey: .task), !task.isEmpty {
            self.content = task
        } else if let name = try? container.decode(String.self, forKey: .name), !name.isEmpty {
            self.content = name
        } else {
            self.content = ""
        }

        self.source = try? container.decode(String.self, forKey: .source)
        self.tags = (try? container.decode([String].self, forKey: .tags)) ?? []
        self.timestamp = try? container.decode(Date.self, forKey: .timestamp)
        self.confidence = try? container.decode(Double.self, forKey: .confidence)
        self.stale = try? container.decode(Bool.self, forKey: .stale)

        if let gitInfo = try? container.decode([String: AnyCodable].self, forKey: .gitInfo) {
            self.gitBranch = gitInfo["branch"]?.value as? String
            self.gitCommit = gitInfo["commit"]?.value as? String
        } else {
            self.gitBranch = nil
            self.gitCommit = nil
        }

        self.factType = try? container.decode(String.self, forKey: .factType)
        if let parentIdInt = try? container.decode(Int.self, forKey: .parentId) {
            self.parentId = String(parentIdInt)
        } else {
            self.parentId = try? container.decode(String.self, forKey: .parentId)
        }
        if let versionGroupIdInt = try? container.decode(Int.self, forKey: .versionGroupId) {
            self.versionGroupId = String(versionGroupIdInt)
        } else {
            self.versionGroupId = try? container.decode(String.self, forKey: .versionGroupId)
        }
        self.isCurrent = try? container.decode(Bool.self, forKey: .isCurrent)
        if let clusterIdInt = try? container.decode(Int.self, forKey: .clusterId) {
            self.clusterId = String(clusterIdInt)
        } else {
            self.clusterId = try? container.decode(String.self, forKey: .clusterId)
        }
        self.inheritanceMode = try? container.decode(String.self, forKey: .inheritanceMode)
        self.decayScore = try? container.decode(Double.self, forKey: .decayScore)
        self.lastRecalledAt = try? container.decode(Date.self, forKey: .lastRecalledAt)
        self.checksum = try? container.decode(String.self, forKey: .checksum)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(content, forKey: .content)
        try container.encodeIfPresent(source, forKey: .source)
        try container.encode(tags, forKey: .tags)
        try container.encodeIfPresent(timestamp, forKey: .timestamp)
        try container.encodeIfPresent(confidence, forKey: .confidence)
        try container.encodeIfPresent(stale, forKey: .stale)
        if let gitBranch = gitBranch, let gitCommit = gitCommit {
            try container.encode(["branch": gitBranch, "commit": gitCommit], forKey: .gitInfo)
        }
        try container.encodeIfPresent(factType, forKey: .factType)
        try container.encodeIfPresent(parentId, forKey: .parentId)
        try container.encodeIfPresent(versionGroupId, forKey: .versionGroupId)
        try container.encodeIfPresent(isCurrent, forKey: .isCurrent)
        try container.encodeIfPresent(clusterId, forKey: .clusterId)
        try container.encodeIfPresent(inheritanceMode, forKey: .inheritanceMode)
        try container.encodeIfPresent(decayScore, forKey: .decayScore)
        try container.encodeIfPresent(lastRecalledAt, forKey: .lastRecalledAt)
        try container.encodeIfPresent(checksum, forKey: .checksum)
    }
}

struct FactUpdateRequest: Codable {
    let content: String
    let tags: [String]
}

struct SkillSuggestion: Codable, Identifiable {
    let id: String
    let name: String
    let description: String?
}
