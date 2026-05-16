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
    readonly property real remaining: state && state.remaining !== undefined ? state.remaining : 0
    readonly property bool flockBonus: state && state.flock_bonus_active ? true : false
    readonly property var crickets: state && state.crickets ? state.crickets : []

    // ---- Camera mirror background ----
    Image {
        id: cameraView
        anchors.fill: parent
        cache: false
        fillMode: Image.PreserveAspectCrop
        source: "image://camera/latest"
        transform: Scale { xScale: -1; origin.x: cameraView.width / 2 }
        // Force refresh — bind to a property that ticks
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

    // Tint overlay nhẹ để sprite + HUD rõ hơn
    Rectangle {
        anchors.fill: parent
        color: "#20000000"
    }

    // ---- Lũy tre bottom ----
    Rectangle {
        id: bamboo
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: parent.height * 0.3
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#005C8A3A" }
            GradientStop { position: 0.5; color: "#FF5C8A3A" }
            GradientStop { position: 1.0; color: "#FF3F6627" }
        }
        Row {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 8
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 18
            Repeater {
                model: 8
                Rectangle {
                    width: 12
                    height: 80 + (index % 3) * 24
                    radius: 6
                    color: "#3F6627"
                    border.color: "#5C8A3A"
                    border.width: 1
                }
            }
        }
    }

    // ---- Cricket sprite layer ----
    Repeater {
        model: root.crickets
        Text {
            text: "🦗"
            font.pixelSize: 56
            x: modelData.x * root.width - width / 2
            y: modelData.y * root.height - height / 2
            opacity: modelData.alive ? 1.0 : 0.0
            Behavior on x { NumberAnimation { duration: 80; easing.type: Easing.Linear } }
            Behavior on y { NumberAnimation { duration: 80; easing.type: Easing.Linear } }
        }
    }

    // ---- Hand landmark overlay (Canvas) ----
    Canvas {
        id: handCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        // Redraw when handLandmarks updates
        Connections {
            target: app
            function onHandLandmarksChanged() { handCanvas.requestPaint() }
        }

        onPaint: {
            const ctx = handCanvas.getContext("2d")
            ctx.reset()
            const hands = app.handLandmarks
            if (!hands || hands.length === 0) return

            ctx.strokeStyle = "#5C8A3A"
            ctx.fillStyle = "#C77B2C"
            ctx.lineWidth = 3

            for (let h = 0; h < hands.length; h++) {
                const hand = hands[h]
                // Skeleton connections — wrist(0) → MCP joints
                const connections = [
                    [0,1],[1,2],[2,3],[3,4],
                    [0,5],[5,6],[6,7],[7,8],
                    [0,9],[9,10],[10,11],[11,12],
                    [0,13],[13,14],[14,15],[15,16],
                    [0,17],[17,18],[18,19],[19,20]
                ]
                for (let c = 0; c < connections.length; c++) {
                    const pair = connections[c]
                    const a = pair[0]
                    const b = pair[1]
                    if (a >= hand.length || b >= hand.length) continue
                    // Mirror x (cam is flipped)
                    const ax = (1 - hand[a].x) * width
                    const ay = hand[a].y * height
                    const bx = (1 - hand[b].x) * width
                    const by = hand[b].y * height
                    ctx.beginPath()
                    ctx.moveTo(ax, ay)
                    ctx.lineTo(bx, by)
                    ctx.stroke()
                }
                // Dots
                for (let i = 0; i < hand.length; i++) {
                    const px = (1 - hand[i].x) * width
                    const py = hand[i].y * height
                    ctx.beginPath()
                    ctx.arc(px, py, 5, 0, 2 * Math.PI)
                    ctx.fill()
                }
            }
        }
    }

    // ---- HUD: score top-left, countdown top-right ----
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.margins: 24
        width: scoreText.implicitWidth + 32
        height: 56
        radius: 28
        color: root.flockBonus ? "#FFC77B2C" : "#FF5C8A3A"
        Text {
            id: scoreText
            anchors.centerIn: parent
            text: "🎯 " + root.score + (root.flockBonus ? "  ×1.5" : "")
            color: "white"
            font.pixelSize: 28
            font.bold: true
        }
    }

    Rectangle {
        visible: root.phase === "playing"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 24
        width: 110
        height: 56
        radius: 28
        color: "#FF3F6627"
        Text {
            anchors.centerIn: parent
            text: Math.ceil(root.remaining) + "s"
            color: "white"
            font.pixelSize: 28
            font.bold: true
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
                text: "🦗 Vẫy tay chào đàn dế!"
                color: "white"
                font.pixelSize: 56
                font.bold: true
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

    // ---- Result overlay ----
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
                text: "Bạn vẫy cho " + (root.state && root.state.crickets_flown ? root.state.crickets_flown : 0) + " con dế bay"
                color: "#FAF6EE"
                font.pixelSize: 32
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Điểm: " + root.score
                color: "#C77B2C"
                font.pixelSize: 48
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // ---- Audio (cricket spawn / cricket flown / result enter) ----
    SoundEffect {
        id: sfxChirp
        source: Qt.resolvedUrl("assets/cricket_chirp.wav")
    }
    SoundEffect {
        id: sfxTing
        source: Qt.resolvedUrl("assets/score_ting.wav")
    }
    SoundEffect {
        id: sfxFanfare
        source: Qt.resolvedUrl("assets/end_fanfare.wav")
    }

    // Track cricket count to trigger sfx when changes
    property int lastCricketCount: 0
    property int lastFlownCount: 0
    property string lastPhase: ""

    onCricketsChanged: {
        if (crickets.length > lastCricketCount) {
            sfxChirp.play()
        }
        lastCricketCount = crickets.length
        // crickets_flown increments
        const flown = state && state.crickets_flown ? state.crickets_flown : 0
        if (flown > lastFlownCount) {
            sfxTing.play()
        }
        lastFlownCount = flown
    }

    onPhaseChanged: {
        if (phase === "result" && lastPhase !== "result") {
            sfxFanfare.play()
        }
        lastPhase = phase
    }
}
