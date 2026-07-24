import SwiftUI

/// A modal popup that can be dismissed three ways: clicking the dimmed
/// backdrop, pressing Esc, or clicking the floating X. Native .sheet on
/// macOS supports none of those reliably, which left users stuck in popups
/// (fact tree, timeline, system prompt…).
struct DismissablePopup<PopupContent: View>: ViewModifier {
    @Binding var isPresented: Bool
    var onDismiss: (() -> Void)? = nil
    @ViewBuilder var popupContent: () -> PopupContent

    func body(content: Content) -> some View {
        content.overlay {
            if isPresented {
                ZStack {
                    Color.black.opacity(0.45)
                        .ignoresSafeArea()
                        .contentShape(Rectangle())
                        .onTapGesture { dismiss() }
                        .transition(.opacity)

                    popupContent()
                        .background(Color.acruxCard)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                        .overlay(alignment: .topTrailing) {
                            Button { dismiss() } label: {
                                Image(systemName: "xmark")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundStyle(.primary)
                                    .padding(7)
                                    .background(Circle().fill(Color.acruxElevated))
                                    .shadow(color: .black.opacity(0.35), radius: 6, x: 0, y: 2)
                            }
                            .buttonStyle(AnimatedIconButtonStyle())
                            .keyboardShortcut(.cancelAction)
                            .offset(x: 12, y: -12)
                        }
                        .shadow(color: .black.opacity(0.5), radius: 30, x: 0, y: 12)
                        .frame(maxWidth: 760, maxHeight: 620)
                        .contentShape(Rectangle())
                        .onTapGesture {} // swallow taps so they don't reach the backdrop
                        .transition(.scale(scale: 0.92).combined(with: .opacity).combined(with: .offset(y: 10)))
                }
                .zIndex(100)
            }
        }
        .animation(Theme.springEntrance, value: isPresented)
    }

    private func dismiss() {
        isPresented = false
        onDismiss?()
    }
}

extension View {
    func dismissablePopup<PopupContent: View>(
        isPresented: Binding<Bool>,
        onDismiss: (() -> Void)? = nil,
        @ViewBuilder content: @escaping () -> PopupContent
    ) -> some View {
        modifier(DismissablePopup(isPresented: isPresented, onDismiss: onDismiss, popupContent: content))
    }
}
