import CoreGraphics
import Foundation
let opts: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
if let list = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) as? [[String: Any]] {
    for w in list where (w["kCGWindowOwnerName"] as? String) == "Logic Pro" {
        let b = w["kCGWindowBounds"] as? [String: Any] ?? [:]
        print(w["kCGWindowNumber"] ?? 0, "|", w["kCGWindowLayer"] ?? -1, "|", w["kCGWindowName"] as? String ?? "", "|", b["X"] ?? 0, b["Y"] ?? 0, b["Width"] ?? 0, b["Height"] ?? 0)
    }
}
