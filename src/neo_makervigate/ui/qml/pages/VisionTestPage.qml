import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../singletons" as Sing

// Phase 1 demo — full-screen camera preview + skeleton overlay + FPS readout.
Item {
    id: page

    Rectangle {
        anchors.fill: parent
        color: Sing.NeoConstants.background
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        Text {
            text: "Phase 1 — Vision Test"
            font.pixelSize: Sing.NeoConstants.fontTitle
            color: Sing.NeoConstants.tre
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1F2937"
            border.color: Sing.NeoConstants.de
            border.width: 2
            radius: 12
            clip: true

            CameraPreview { anchors.fill: parent }
            SkeletonOverlay { anchors.fill: parent }

            Rectangle {
                visible: !app.cameraConnected
                anchors.centerIn: parent
                width: 380
                height: 80
                radius: 12
                color: "#C62828"
                opacity: 0.85

                Text {
                    anchors.centerIn: parent
                    text: "Camera chưa sẵn sàng…"
                    color: "white"
                    font.pixelSize: 22
                    font.bold: true
                }
            }
        }

        RowLayout {
            spacing: 28
            Layout.alignment: Qt.AlignHCenter

            Text {
                text: "FPS: " + app.visionFps.toFixed(1)
                font.pixelSize: 22
                color: Sing.NeoConstants.textPrimary
            }
            Text {
                text: "Hands: " + app.handLandmarks.length
                font.pixelSize: 22
                color: Sing.NeoConstants.textPrimary
            }
            Text {
                text: "Gesture: " + (app.lastGesture || "—")
                font.pixelSize: 22
                color: Sing.NeoConstants.de
            }
        }

        Text {
            text: "Vẫy tay trước webcam — chấm xanh = landmarks. ESC/Cmd-Q để thoát."
            font.pixelSize: 16
            color: Sing.NeoConstants.textPrimary
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
