import SwiftUI

struct CommandPaletteItem: Identifiable {
    let id = UUID()
    let title: String
    let icon: String
    let disabled: Bool
    let action: () -> Void

    init(title: String, icon: String, disabled: Bool = false, action: @escaping () -> Void) {
        self.title = title
        self.icon = icon
        self.disabled = disabled
        self.action = action
    }
}

struct CommandPaletteView: View {
    @Binding var isPresented: Bool
    @State private var query = ""
    var items: [CommandPaletteItem]

    private var filtered: [CommandPaletteItem] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if q.isEmpty { return items }
        return items.filter { $0.title.lowercased().contains(q) }
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("Type a command…", text: $query)
                    .textFieldStyle(.plain)
                    .font(.system(size: 16))
                Text("⌘⇧P")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
            }
            .padding()
            .background(.ultraThinMaterial)

            List(filtered) { item in
                Button {
                    item.action()
                    isPresented = false
                } label: {
                    HStack(spacing: 12) {
                        Image(systemName: item.icon)
                            .frame(width: 22)
                        Text(item.title)
                            .font(.system(size: 14))
                        Spacer()
                    }
                    .padding(.vertical, 6)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.primary)
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)
                .disabled(item.disabled)
                .opacity(item.disabled ? 0.5 : 1.0)
            }
            .scrollContentBackground(.hidden)
        }
        .frame(minWidth: 480, minHeight: 360)
        .background(Color.acruxCard)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.acruxSubtleBorder, lineWidth: 1)
        )
    }
}
