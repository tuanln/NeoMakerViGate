import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../singletons" as Sing

// Host page cho plugin ui.qml đang active. Loader nạp source từ app.currentQmlPath().
// Nút Back nhỏ ở góc trái trên — gọi app.exitExperience() để quay lại Hub.
Item {
    id: page

    signal backRequested()

    Rectangle {
        anchors.fill: parent
        color: Sing.NeoConstants.background
    }

    // Plugin UI Loader
    Loader {
        id: pluginLoader
        anchors.fill: parent
        source: app.currentQmlPath()
        active: app.currentExperience !== ""
        onStatusChanged: {
            if (status === Loader.Error) {
                console.warn("ExperienceContainerPage: failed to load", source)
            }
        }
    }

    // Nút Back
    Rectangle {
        id: backBtn
        x: 16
        y: 16
        width: 88
        height: 44
        radius: 22
        color: Sing.NeoConstants.tre
        border.color: Sing.NeoConstants.treDark
        border.width: 2

        Text {
            anchors.centerIn: parent
            text: "← Hub"
            color: "white"
            font.pixelSize: 18
            font.bold: true
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: page.backRequested()
        }
    }

    // Badge gesture (debug — hiện gesture mới nhất từ vision)
    Rectangle {
        visible: app.lastGesture !== ""
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        width: gestureText.implicitWidth + 24
        height: 32
        radius: 16
        color: Sing.NeoConstants.de
        opacity: 0.9

        Text {
            id: gestureText
            anchors.centerIn: parent
            text: "Cử chỉ: " + app.lastGesture
            color: "white"
            font.pixelSize: 14
            font.bold: true
        }
    }
}
