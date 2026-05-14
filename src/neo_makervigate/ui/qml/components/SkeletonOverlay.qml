import QtQuick

// Vẽ landmarks (hands + pose) lên trên CameraPreview.
// Phase 1: hand landmarks (21 điểm × 0-2 tay) làm chấm tròn.
// Phase 4 sẽ thêm Pose 33 điểm + connections (xương).
Canvas {
    id: canvas
    anchors.fill: parent
    antialiasing: true

    // Repaint khi landmark thay đổi
    property var hands: app.handLandmarks
    onHandsChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        if (!hands || hands.length === 0) return

        ctx.fillStyle = "#4ADE80"
        for (var h = 0; h < hands.length; h++) {
            var hand = hands[h]
            for (var i = 0; i < hand.length; i++) {
                var lm = hand[i]
                var px = lm.x * width
                var py = lm.y * height
                ctx.beginPath()
                ctx.arc(px, py, 5, 0, Math.PI * 2)
                ctx.fill()
            }
        }
    }
}
