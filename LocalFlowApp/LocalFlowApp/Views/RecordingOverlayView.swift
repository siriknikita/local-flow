//
//  RecordingOverlayView.swift
//  LocalFlowApp
//
//  Recording overlay with waveform visualization
//

import SwiftUI

struct RecordingOverlayView: View {
    @ObservedObject var websocketService: WebSocketService
    @ObservedObject var backendService: BackendService
    @State private var isVisible = false
    
    var onCancel: () -> Void
    var onStop: () -> Void
    
    var body: some View {
        VStack(spacing: 20) {
            // Status label
            Text("Recording...")
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(.white)
            
            // Waveform visualization
            WaveformView(data: websocketService.waveformData)
                .frame(height: 80)
                .background(Color(white: 0.1))
                .cornerRadius(8)
            
            // Buttons
            HStack(spacing: 15) {
                Button("Cancel (Esc)") {
                    onCancel()
                }
                .buttonStyle(OverlayButtonStyle(color: .red))
                
                Button("Stop (Enter)") {
                    onStop()
                }
                .buttonStyle(OverlayButtonStyle(color: .green))
            }
        }
        .padding(20)
        .frame(width: 400, height: 200)
        .background(Color(white: 0.15))
        .cornerRadius(15)
        .shadow(radius: 10)
    }
}

struct WaveformView: View {
    let data: [Float]
    
    var body: some View {
        GeometryReader { geometry in
            if data.isEmpty {
                Text("Waiting for audio...")
                    .foregroundColor(.gray)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Canvas { context, size in
                    let centerY = size.height / 2
                    let width = size.width
                    
                    // Draw center line
                    context.stroke(
                        Path { path in
                            path.move(to: CGPoint(x: 0, y: centerY))
                            path.addLine(to: CGPoint(x: width, y: centerY))
                        },
                        with: .color(.gray.opacity(0.3)),
                        lineWidth: 1
                    )
                    
                    // Draw waveform
                    if data.count > 1 {
                        let maxAmplitude = data.max() ?? 1.0
                        let normalizedData = data.map { $0 / maxAmplitude }
                        
                        var path = Path()
                        let stepX = width / CGFloat(normalizedData.count - 1)
                        
                        for (index, amplitude) in normalizedData.enumerated() {
                            let x = CGFloat(index) * stepX
                            let normalized = CGFloat(amplitude) * 2 - 1 // Center around 0
                            let y = centerY - (normalized * (size.height / 2 - 10))
                            
                            if index == 0 {
                                path.move(to: CGPoint(x: x, y: y))
                            } else {
                                path.addLine(to: CGPoint(x: x, y: y))
                            }
                        }
                        
                        context.stroke(path, with: .color(.green), lineWidth: 2)
                        
                        // Draw current amplitude indicator
                        if let lastAmplitude = normalizedData.last {
                            let normalized = CGFloat(lastAmplitude) * 2 - 1
                            let currentY = centerY - (normalized * (size.height / 2 - 10))
                            let indicatorRect = CGRect(
                                x: width - 15,
                                y: currentY - 3,
                                width: 10,
                                height: 6
                            )
                            context.fill(
                                Path(ellipseIn: indicatorRect),
                                with: .color(.yellow)
                            )
                        }
                    }
                }
            }
        }
    }
}

struct OverlayButtonStyle: ButtonStyle {
    let color: Color
    
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(.white)
            .padding(.horizontal, 20)
            .padding(.vertical, 8)
            .background(color)
            .cornerRadius(8)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
    }
}

