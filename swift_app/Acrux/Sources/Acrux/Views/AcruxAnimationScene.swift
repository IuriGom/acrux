import SpriteKit

final class AcruxAnimationScene: SKScene {
    private var stars: [SKShapeNode] = []

    override func didMove(to view: SKView) {
        backgroundColor = .clear
        scaleMode = .resizeFill

        // Acrux stars (white only)
        let starCount = 120
        for _ in 0..<starCount {
            let star = SKShapeNode(circleOfRadius: CGFloat.random(in: 0.8...2.2))
            star.fillColor = .white
            star.strokeColor = .clear
            star.glowWidth = 2.5
            star.position = CGPoint(
                x: CGFloat.random(in: 0...size.width),
                y: CGFloat.random(in: 0...size.height)
            )
            addChild(star)
            stars.append(star)

            let twinkle = SKAction.repeatForever(SKAction.sequence([
                SKAction.fadeAlpha(to: 0.2, duration: Double.random(in: 0.6...1.4)),
                SKAction.fadeAlpha(to: 1.0, duration: Double.random(in: 0.6...1.4))
            ]))
            star.run(twinkle)

            let drift = SKAction.repeatForever(SKAction.sequence([
                SKAction.moveBy(x: CGFloat.random(in: -20...20), y: CGFloat.random(in: -20...20), duration: Double.random(in: 4...8)),
                SKAction.moveBy(x: CGFloat.random(in: -20...20), y: CGFloat.random(in: -20...20), duration: Double.random(in: 4...8))
            ]))
            star.run(drift)
        }
    }
}
