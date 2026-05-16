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
}
