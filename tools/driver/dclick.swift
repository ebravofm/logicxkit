import CoreGraphics
import Foundation
let a = CommandLine.arguments
let p = CGPoint(x: Double(a[1])!, y: Double(a[2])!)
let move = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: .left)!
move.post(tap: .cghidEventTap); usleep(80000)
for n in 1...2 {
    let d = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: p, mouseButton: .left)!
    d.setIntegerValueField(.mouseEventClickState, value: Int64(n)); d.post(tap: .cghidEventTap); usleep(40000)
    let u = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: p, mouseButton: .left)!
    u.setIntegerValueField(.mouseEventClickState, value: Int64(n)); u.post(tap: .cghidEventTap); usleep(90000)
}
