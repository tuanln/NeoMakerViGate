import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../singletons" as Sing

Item {
    id: page
    signal wakeRequested()

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#FAF6EE" }
            GradientStop { position: 1.0; color: "#E8D9B5" }
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 32
        width: parent.width * 0.7

        Text {
            text: "🏛️ 🦗 ✨"
            font.pixelSize: 120
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: "Cổng Làng Maker"
            font.pixelSize: 72
            font.bold: true
            color: Sing.NeoConstants.tre
            Layout.alignment: Qt.AlignHCenter
        }

        Text {
            text: "Chạm màn hình hoặc vẫy tay\nđể bắt đầu"
            font.pixelSize: 36
            color: Sing.NeoConstants.de
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
        }

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 24
            height: 24
            radius: 12
            color: Sing.NeoConstants.gach
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                NumberAnimation { to: 0.2; duration: 800; easing.type: Easing.InOutQuad }
                NumberAnimation { to: 1.0; duration: 800; easing.type: Easing.InOutQuad }
            }
        }
    }

    Text {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 40
        text: "Maker Việt × Dế Foundation × ThingEdu"
        font.pixelSize: 16
        color: Sing.NeoConstants.textPrimary
        opacity: 0.5
    }

    MouseArea {
        anchors.fill: parent
        onClicked: page.wakeRequested()
    }

    // Hand-detect wake — when handLandmarks non-empty for ≥0.5s
    property real _handDetectedSince: 0
    Connections {
        target: app
        function onHandLandmarksChanged() {
            const hands = app.handLandmarks
            const now = Date.now() / 1000
            if (hands && hands.length > 0) {
                if (page._handDetectedSince === 0) {
                    page._handDetectedSince = now
                } else if (now - page._handDetectedSince >= 0.5) {
                    page.wakeRequested()
                    page._handDetectedSince = 0
                }
            } else {
                page._handDetectedSince = 0
            }
        }
    }
}
