import CoreGraphics
import Foundation
let a = CommandLine.arguments
let p0 = CGPoint(x: Double(a[1])!, y: Double(a[2])!)
let p1 = CGPoint(x: Double(a[3])!, y: Double(a[4])!)
func post(_ t: CGEventType, _ p: CGPoint) { CGEvent(mouseEventSource: nil, mouseType: t, mouseCursorPosition: p, mouseButton: .left)?.post(tap: .cghidEventTap); usleep(60000) }
post(.mouseMoved, p0); post(.leftMouseDown, p0)
let steps = 20
for i in 1...steps { post(.leftMouseDragged, CGPoint(x: p0.x + (p1.x - p0.x) * Double(i) / Double(steps), y: p0.y + (p1.y - p0.y) * Double(i) / Double(steps))) }
post(.leftMouseUp, p1)
