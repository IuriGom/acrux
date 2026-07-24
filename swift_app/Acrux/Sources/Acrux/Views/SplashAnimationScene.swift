import SpriteKit

final class SplashAnimationScene: SKScene {
    private var stars: [SKShapeNode] = []
    private var label: SKLabelNode!

    override func didMove(to view: SKView) {
        backgroundColor = .clear
        scaleMode = .resizeFill
        let center = CGPoint(x: size.width / 2, y: size.height / 2)

        // Brazilian flag stars (white only)
        let starCount = 80
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
        }

        // "Acrux" standing out
        label = SKLabelNode(text: "Acrux")
        label.fontName = ".AppleSystemUIFontBold"
        label.fontSize = min(size.width, size.height) * 0.18
        label.fontColor = .white
        label.position = center
        label.zPosition = 10

        let glow = SKLabelNode(text: "Acrux")
        glow.fontName = label.fontName
        glow.fontSize = label.fontSize
        glow.fontColor = SKColor(white: 0.7, alpha: 0.6)
        glow.position = CGPoint(x: center.x + 2, y: center.y - 2)
        glow.zPosition = 9

        addChild(glow)
        addChild(label)

        let pulse = SKAction.repeatForever(SKAction.sequence([
            SKAction.scale(to: 1.04, duration: 2.0),
            SKAction.scale(to: 1.0, duration: 2.0)
        ]))
        label.run(pulse)
    }
}
