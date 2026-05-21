import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../../ui/qml/singletons" as Sing

Item {
    id: root
    anchors.fill: parent

    readonly property var state: app.experienceState
    readonly property string phase: state && state.phase ? state.phase : "intro"
    readonly property int score: state && state.score !== undefined ? state.score : 0
    readonly property real holdProgress: state && state.hold_progress !== undefined ? state.hold_progress : 0.0
    readonly property real holdRequired: state && state.hold_required !== undefined ? state.hold_required : 2.0
    readonly property int matchThreshold: state && state.match_threshold !== undefined ? state.match_threshold : 65
    readonly property var currentPose: state && state.current_pose ? state.current_pose : null
    readonly property bool showHint: state && state.show_hint ? true : false
    readonly property var completedPoses: state && state.completed_poses ? state.completed_poses : []
    readonly property int totalScore: state && state.total_score !== undefined ? state.total_score : 0
    readonly property string bestPoseId: state && state.best_pose_id ? state.best_pose_id : ""
    readonly property int poseCount: state && state.pose_count !== undefined ? state.pose_count : 5
    readonly property int poseIndex: state && state.pose_index !== undefined ? state.pose_index : 0

    // Camera mirror background
    Image {
        id: cameraView
        anchors.fill: parent
        cache: false
        fillMode: Image.PreserveAspectCrop
        source: "image://camera/latest"
        transform: Scale { xScale: -1; origin.x: cameraView.width / 2 }
        property int tick: 0
        Timer {
            interval: 33
            running: true
            repeat: true
            onTriggered: {
                cameraView.tick++
                cameraView.source = "image://camera/latest?t=" + cameraView.tick
            }
        }
    }

    Rectangle { anchors.fill: parent; color: "#20000000" }

    // Face landmark overlay — dots only (17 key points)
    Canvas {
        id: faceCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        Connections {
            target: app
            function onFaceLandmarksChanged() { faceCanvas.requestPaint() }
        }

        onPaint: {
            const ctx = faceCanvas.getContext("2d")
            ctx.reset()
            const face = app.faceLandmarks
            if (!face || face.length < 386) return

            ctx.fillStyle = "#C77B2C"
            // Key landmark indices (subset)
            const indices = [
                1, 13, 14, 78, 308,         // nose + mouth
                33, 133, 145, 159, 263, 362, 374, 386,  // eyes
                55, 105, 285, 334           // brows
            ]
            for (let i = 0; i < indices.length; i++) {
                const idx = indices[i]
                if (idx >= face.length) continue
                const px = (1 - face[idx].x) * width  // mirror x
                const py = face[idx].y * height
                ctx.beginPath()
                ctx.arc(px, py, 4, 0, 2 * Math.PI)
                ctx.fill()
            }
        }
    }

    // Pose card top center
    Rectangle {
        visible: root.currentPose !== null && root.phase === "posing"
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 24
        width: poseCardCol.implicitWidth + 48
        height: poseCardCol.implicitHeight + 24
        radius: 20
        color: "#E03F6627"
        border.color: "#FFC77B2C"
        border.width: 3

        ColumnLayout {
            id: poseCardCol
            anchors.centerIn: parent
            spacing: 6
            Text {
                text: (root.currentPose ? root.currentPose.emoji : "") + "  " + (root.currentPose ? root.currentPose.title : "")
                color: "white"
                font.pixelSize: 40
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.currentPose ? root.currentPose.subtitle : ""
                color: "#FAF6EE"
                font.pixelSize: 22
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Biểu cảm " + (root.poseIndex + 1) + " / " + root.poseCount
                color: "#FAF6EE"
                opacity: 0.7
                font.pixelSize: 16
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // Bottom HUD: robot face + hold bar + score
    Rectangle {
        visible: root.phase === "posing"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 24
        height: 140
        radius: 24
        color: "#E0000000"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 24

            Item {
                Layout.preferredWidth: 120
                Layout.fillHeight: true
                Text {
                    anchors.centerIn: parent
                    text: {
                        const s = root.score
                        if (s >= root.matchThreshold) return "😄"
                        if (s >= 40) return "🙂"
                        return "😐"
                    }
                    font.pixelSize: 96
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    Rectangle {
                        anchors.fill: parent
                        radius: 16
                        color: "#FF1F3018"
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: 4
                            width: Math.min(1, root.holdProgress / root.holdRequired) * (parent.width - 8)
                            radius: 12
                            color: (root.holdProgress / root.holdRequired) > 0.66 ? "#FFC77B2C" : "#FF5C8A3A"
                            Behavior on width { NumberAnimation { duration: 50 } }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: root.holdProgress.toFixed(1) + "s / " + root.holdRequired.toFixed(1) + "s"
                        color: "white"
                        font.pixelSize: 18
                        font.bold: true
                    }
                }
                Text {
                    text: "Điểm: " + root.score + "/100  (cần " + root.matchThreshold + "+)"
                    color: "white"
                    font.pixelSize: 22
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
    }

    // Intro overlay
    Rectangle {
        visible: root.phase === "intro"
        anchors.fill: parent
        color: "#A0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🤖 Bắt chước 5 biểu cảm!"
                color: "white"
                font.pixelSize: 56
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "😄  😮  😉  🤨  🙅"
                color: "#FAF6EE"
                font.pixelSize: 64
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Sẵn sàng nhé..."
                color: "#FAF6EE"
                font.pixelSize: 28
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // Result overlay
    Rectangle {
        visible: root.phase === "result"
        anchors.fill: parent
        color: "#C0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🎉 Tuyệt vời!"
                color: "white"
                font.pixelSize: 72
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Tổng điểm: " + root.totalScore + " / 500"
                color: "#C77B2C"
                font.pixelSize: 48
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.bestPoseId !== "" ? "Pose đẹp nhất: " + root.bestPoseId : ""
                color: "#FAF6EE"
                font.pixelSize: 28
                visible: root.bestPoseId !== ""
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
