// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "LocalFlowApp",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "LocalFlowApp",
            targets: ["LocalFlowApp"]
        )
    ],
    targets: [
        .executableTarget(
            name: "LocalFlowApp",
            path: "LocalFlowApp"
        )
    ]
)
