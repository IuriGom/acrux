import Foundation

struct Message: Identifiable, Codable, Equatable {
    let id: UUID
    var role: String
    var content: String
    var reasoning: String?
    var toolCalls: [ToolCall]?
    var toolResults: [ToolResult]?
    var timestamp: Date
    var pinned: Bool?
    var checkpoint: MessageCheckpoint?
}

struct MessageCheckpoint: Codable, Equatable {
    let turn: Int
    let toolName: String?
    let message: String?
}
