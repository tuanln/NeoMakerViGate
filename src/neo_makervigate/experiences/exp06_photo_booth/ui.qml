import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../ui/qml/singletons" as Sing

Item {
    id: root
    anchors.fill: parent

    readonly property var state: app.experienceState
    readonly property string phase: state && state.phase ? state.phase : "intro"
    readonly property var backgrounds: state && state.backgrounds ? state.backgrounds : []
    readonly property int selectedIdx: state && state.selected_bg_index !== undefined ? state.selected_bg_index : 0
    readonly property real vSignProgress: state && state.v_sign_progress !== undefined ? state.v_sign_progress : 0.0
    readonly property real countdownRemaining: state && state.countdown_remaining !== undefined ? state.countdown_remaining : 0.0
    readonly property string processingStatus: state && state.processing_status ? state.processing_status : ""
    readonly property string caption: state && state.caption ? state.caption : ""

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

    // Background ghost overlay during STAGE
    Image {
        visible: root.phase === "stage" && root.backgrounds.length > 0
        anchors.fill: parent
        opacity: 0.3
        fillMode: Image.PreserveAspectCrop
        source: root.backgrounds.length > 0 ? "file://" + root.backgrounds[root.selectedIdx].path : ""
        cache: false
    }

    // INTRO overlay
    Rectangle {
        visible: root.phase === "intro"
        anchors.fill: parent
        color: "#A0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "📸 Chào mừng đến Photo Booth!"
                color: "white"
                font.pixelSize: 56
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Chọn cảnh em thích, làm chữ V để chụp."
                color: "#FAF6EE"
                font.pixelSize: 28
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // SELECT — thumbnails bottom row
    Rectangle {
        visible: root.phase === "select"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 200
        color: "#C0000000"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8
            Text {
                text: "Chỉ tay (POINT) để đổi cảnh — tự chọn sau 3 giây"
                color: "white"
                font.pixelSize: 18
                Layout.alignment: Qt.AlignHCenter
            }
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 16
                Repeater {
                    model: root.backgrounds
                    Rectangle {
                        Layout.preferredWidth: 200
                        Layout.preferredHeight: 130
                        radius: 12
                        color: "white"
                        border.color: index === root.selectedIdx ? Sing.NeoConstants.de : "transparent"
                        border.width: index === root.selectedIdx ? 6 : 0
                        Image {
                            anchors.fill: parent
                            anchors.margins: 4
                            source: "file://" + modelData.path
                            fillMode: Image.PreserveAspectCrop
                            cache: false
                        }
                        Text {
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.emoji + " " + modelData.title
                            color: "white"
                            font.pixelSize: 14
                            font.bold: true
                            style: Text.Outline
                            styleColor: "black"
                        }
                    }
                }
            }
        }
    }

    // STAGE — V_SIGN prompt + hold bar
    Rectangle {
        visible: root.phase === "stage"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 120
        color: "#A0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 12
            Text {
                text: "✌️ Làm chữ V để chụp!"
                color: "white"
                font.pixelSize: 32
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Rectangle {
                Layout.preferredWidth: 400
                Layout.preferredHeight: 20
                radius: 10
                color: "#FF1F3018"
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 3
                    width: root.vSignProgress * (parent.width - 6)
                    radius: 8
                    color: Sing.NeoConstants.tre
                }
            }
        }
    }

    // COUNTDOWN — giant number
    Text {
        visible: root.phase === "countdown"
        anchors.centerIn: parent
        text: {
            const r = Math.ceil(root.countdownRemaining)
            if (r <= 0) return "📸"
            return String(r)
        }
        color: "white"
        font.pixelSize: 200
        font.bold: true
        style: Text.Outline
        styleColor: "black"
    }

    // PROCESSING — spinner + status
    Rectangle {
        visible: root.phase === "processing"
        anchors.fill: parent
        color: "#C0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: true
            }
            Text {
                text: "Đang chụp + viết caption..."
                color: "white"
                font.pixelSize: 32
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.processingStatus
                color: "#FAF6EE"
                font.pixelSize: 20
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
