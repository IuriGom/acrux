// swift-tools-version:6.0
import PackageDescription

let package = Package(
    name: "Acrux",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "Acrux", targets: ["Acrux"])
    ],
    targets: [
        .executableTarget(
            name: "Acrux",
            path: "Sources/Acrux",
            swiftSettings: [.enableExperimentalFeature("StrictConcurrency")]
        )
    ]
)
