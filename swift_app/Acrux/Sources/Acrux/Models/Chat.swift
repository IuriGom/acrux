import Foundation

struct Chat: Identifiable, Codable, Hashable {
    var id: UUID
    var title: String
    var workspace: String
    var model: String
    var allowedTools: [String]
    var autoAccept: Bool
    var useMemory: Bool
    var loopMode: Bool
    var checkpointInterval: Int
    var messages: [Message]
    var createdAt: Date
    var updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id, title, workspace, model, allowedTools, autoAccept, useMemory, loopMode, checkpointInterval, messages, createdAt, updatedAt
    }

    init(id: UUID, title: String, workspace: String, model: String, allowedTools: [String], autoAccept: Bool, useMemory: Bool, loopMode: Bool = false, checkpointInterval: Int = 1, messages: [Message], createdAt: Date, updatedAt: Date) {
        self.id = id
        self.title = title
        self.workspace = workspace
        self.model = model
        self.allowedTools = allowedTools
        self.autoAccept = autoAccept
        self.useMemory = useMemory
        self.loopMode = loopMode
        self.checkpointInterval = checkpointInterval
        self.messages = messages
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        workspace = try container.decode(String.self, forKey: .workspace)
        model = try container.decode(String.self, forKey: .model)
        allowedTools = try container.decode([String].self, forKey: .allowedTools)
        autoAccept = try container.decode(Bool.self, forKey: .autoAccept)
        useMemory = try container.decodeIfPresent(Bool.self, forKey: .useMemory) ?? true
        loopMode = try container.decodeIfPresent(Bool.self, forKey: .loopMode) ?? false
        checkpointInterval = try container.decodeIfPresent(Int.self, forKey: .checkpointInterval) ?? 1
        messages = try container.decode([Message].self, forKey: .messages)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        updatedAt = try container.decode(Date.self, forKey: .updatedAt)
    }
}

extension Chat {
    static func == (lhs: Chat, rhs: Chat) -> Bool {
        lhs.id == rhs.id
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}
