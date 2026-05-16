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
}
