import QtQuick
import QtQuick.Layouts

Rectangle {
    color: "#FAF6EE"

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 24

        Text {
            text: "📸 Photo Booth Cổng Làng"
            font.pixelSize: 64
            font.bold: true
            color: "#5C8A3A"
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "Phase 5 sẽ implement chụp + QR\nPhase 6 sẽ thêm ghép nền AR + Qwen caption"
            font.pixelSize: 24
            color: "#3F6627"
            horizontalAlignment: Text.AlignHCenter
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "MediaPipe: Selfie Segmentation + Pose | Qwen: ✅ caption"
            font.pixelSize: 18
            color: "#C77B2C"
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
