import SwiftUI
import SpriteKit

struct SplashView: View {
    var body: some View {
        ZStack {
            Color.acruxBg.ignoresSafeArea()
            SpriteView(
                scene: SplashAnimationScene(size: CGSize(width: 1400, height: 900)),
                options: [.allowsTransparency]
            )
            .ignoresSafeArea()
        }
    }
}
