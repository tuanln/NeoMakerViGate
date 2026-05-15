import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// P2 stub UI — sẽ thay bằng gameplay thực ở P3
Rectangle {
    color: "#FAF6EE"

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 24

        Text {
            text: "🦗 Vẫy Chào Dế"
            font.pixelSize: 64
            font.bold: true
            color: "#5C8A3A"
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "Phase 3 sẽ implement gameplay\nVẫy tay → đàn dế bay khỏi lũy tre"
            font.pixelSize: 24
            color: "#3F6627"
            horizontalAlignment: Text.AlignHCenter
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "MediaPipe module: Hands"
            font.pixelSize: 18
            color: "#C77B2C"
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
