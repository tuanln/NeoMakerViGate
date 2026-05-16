import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../../ui/qml/singletons" as Sing

Item {
    id: root
    anchors.fill: parent

    // ---- State helpers from app.experienceState ----
    readonly property var state: app.experienceState
    readonly property string phase: state && state.phase ? state.phase : "intro"
    readonly property int score: state && state.score !== undefined ? state.score : 0
    readonly property real holdProgress: state && state.hold_progress !== undefined ? state.hold_progress : 0.0
    readonly property real holdRequired: state && state.hold_required !== undefined ? state.hold_required : 3.0
    readonly property int matchThreshold: state && state.match_threshold !== undefined ? state.match_threshold : 65
    readonly property var currentPose: state && state.current_pose ? state.current_pose : null
    readonly property bool showHint: state && state.show_hint ? true : false
    readonly property var completedPoses: state && state.completed_poses ? state.completed_poses : []
    readonly property int totalScore: state && state.total_score !== undefined ? state.total_score : 0
    readonly property string bestPoseId: state && state.best_pose_id ? state.best_pose_id : ""
    readonly property int poseCount: state && state.pose_count !== undefined ? state.pose_count : 5
    readonly property int poseIndex: state && state.pose_index !== undefined ? state.pose_index : 0

    // ---- Camera mirror background ----
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

    Rectangle {
        anchors.fill: parent
        color: "#20000000"
    }

    // ---- Pose skeleton overlay (33 landmarks) ----
    Canvas {
        id: poseCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        Connections {
            target: app
            function onPoseLandmarksChanged() { poseCanvas.requestPaint() }
        }

        onPaint: {
            const ctx = poseCanvas.getContext("2d")
            ctx.reset()
            const pose = app.poseLandmarks
            if (!pose || pose.length < 33) return

            ctx.strokeStyle = "#5C8A3A"
            ctx.fillStyle = "#C77B2C"
            ctx.lineWidth = 4

            // MediaPipe Pose connections (subset): torso + arms + legs + face cue
            const connections = [
                // Torso quad
                [11, 12], [12, 24], [24, 23], [23, 11],
                // Left arm
                [11, 13], [13, 15],
                // Right arm
                [12, 14], [14, 16],
                // Left leg
                [23, 25], [25, 27],
                // Right leg
                [24, 26], [26, 28],
                // Face nose-shoulders
                [0, 11], [0, 12]
            ]

            for (let c = 0; c < connections.length; c++) {
                const pair = connections[c]
                const a = pair[0]
                const b = pair[1]
                if (a >= pose.length || b >= pose.length) continue
                const ax = (1 - pose[a].x) * width
                const ay = pose[a].y * height
                const bx = (1 - pose[b].x) * width
                const by = pose[b].y * height
                ctx.beginPath()
                ctx.moveTo(ax, ay)
                ctx.lineTo(bx, by)
                ctx.stroke()
            }
            // Dots
            for (let i = 0; i < pose.length; i++) {
                const px = (1 - pose[i].x) * width
                const py = pose[i].y * height
                ctx.beginPath()
                ctx.arc(px, py, 5, 0, 2 * Math.PI)
                ctx.fill()
            }
        }
    }

    // ---- Pose card top center ----
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
            spacing: 4
            Text {
                text: (root.currentPose ? root.currentPose.emoji : "") + "  " + (root.currentPose ? root.currentPose.title : "")
                color: "white"
                font.pixelSize: 36
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.currentPose ? root.currentPose.subtitle : ""
                color: "#FAF6EE"
                font.pixelSize: 18
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Tư thế " + (root.poseIndex + 1) + " / " + root.poseCount
                color: "#FAF6EE"
                opacity: 0.7
                font.pixelSize: 14
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // ---- Bottom HUD: robot face + hold bar + score ----
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

            // Robot face widget
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

            // Center column: hold bar + score
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8

                // Hold progress bar
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

                // Score number
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

    // ---- Intro overlay ----
    Rectangle {
        visible: root.phase === "intro"
        anchors.fill: parent
        color: "#A0000000"

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🤖 Bắt chước Robot 5 tư thế!"
                color: "white"
                font.pixelSize: 56
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "✝️  🌳  ⭐  🙌  🌵"
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

    // ---- Hint overlay (semi-transparent, when stuck 15s+) ----
    Rectangle {
        visible: root.showHint && root.phase === "posing"
        anchors.fill: parent
        color: "#40000000"

        Text {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 200
            anchors.horizontalCenter: parent.horizontalCenter
            text: "💡 Thử bắt chước hình " + (root.currentPose ? root.currentPose.emoji : "")
            color: "white"
            font.pixelSize: 32
            font.bold: true
            style: Text.Outline
            styleColor: "black"
        }
    }

    // ---- Result overlay ----
    Rectangle {
        visible: root.phase === "result"
        anchors.fill: parent
        color: "#C0000000"

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🎉 Hoàn thành!"
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
                text: root.bestPoseId !== "" ? "Tư thế giỏi nhất: " + root.bestPoseId : ""
                color: "#FAF6EE"
                font.pixelSize: 28
                visible: root.bestPoseId !== ""
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // ---- Audio ----
    SoundEffect {
        id: sfxLocked
        source: Qt.resolvedUrl("assets/pose_locked.wav")
    }
    SoundEffect {
        id: sfxSkipped
        source: Qt.resolvedUrl("assets/pose_skipped.wav")
    }

    // Track completed count to play sfx on change
    property int lastCompletedCount: 0
    property string lastPhase: ""

    onCompletedPosesChanged: {
        const count = completedPoses.length
        if (count > lastCompletedCount) {
            // Lookup most recent completed
            const last = completedPoses[count - 1]
            if (last && last.skipped) {
                sfxSkipped.play()
            } else {
                sfxLocked.play()
            }
        }
        lastCompletedCount = count
    }

    onPhaseChanged: {
        lastPhase = phase
    }
}
