pragma Singleton
import QtQuick

QtObject {
    // Brand colors — Dế Foundation
    readonly property color tre:         "#5C8A3A"
    readonly property color treDark:     "#3F6627"
    readonly property color de:          "#C77B2C"
    readonly property color gach:        "#B85C38"
    readonly property color song:        "#2A5C8A"
    readonly property color accent:      "#E8C547"
    readonly property color background:  "#FAF6EE"
    readonly property color surface:     "#FFFCF5"
    readonly property color textPrimary: "#1F2937"
    readonly property color success:     "#2E7D32"
    readonly property color warning:     "#FF8F00"
    readonly property color error:       "#C62828"

    // Typography
    property bool largeTextMode: false
    readonly property real textScale:  largeTextMode ? 1.25 : 1.0
    readonly property int fontTitle:   Math.round(40 * textScale)
    readonly property int fontBody:    Math.round(24 * textScale)
    readonly property int fontButton:  Math.round(24 * textScale)
    readonly property int fontScore:   Math.round(72 * textScale)

    // Touch targets
    readonly property int touchMin:      largeTextMode ? 64 : 56
    readonly property int cardWidth:     320
    readonly property int cardHeight:    240
    readonly property int previewWidth:  1280
    readonly property int previewHeight: 720

    // Animation
    readonly property int animFast:    200
    readonly property int animNormal:  400
    readonly property int animSlow:    800

    // Vision-specific
    readonly property int targetVisionFps: 15
    readonly property color landmarkColor: "#4ADE80"
    readonly property real idleTimeoutSec: 90
}
