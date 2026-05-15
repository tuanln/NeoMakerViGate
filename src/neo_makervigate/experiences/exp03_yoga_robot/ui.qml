import QtQuick
import QtQuick.Layouts

Rectangle {
    color: "#FAF6EE"

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 24

        Text {
            text: "🧘 Yoga Robot"
            font.pixelSize: 64
            font.bold: true
            color: "#5C8A3A"
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "Phase 4 sẽ implement pose matching\n5 tư thế mục tiêu — giữ 3s mỗi pose"
            font.pixelSize: 24
            color: "#3F6627"
            horizontalAlignment: Text.AlignHCenter
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "MediaPipe module: Pose (33 landmarks)"
            font.pixelSize: 18
            color: "#C77B2C"
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
