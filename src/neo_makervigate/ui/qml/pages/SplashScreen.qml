import QtQuick
import QtQuick.Layouts

Item {
    id: splash
    signal splashDone()

    Rectangle {
        anchors.fill: parent
        color: "#FAF6EE"
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 24

        Text {
            text: "Cổng Làng Maker"
            font.pixelSize: 64
            font.bold: true
            color: "#5C8A3A"
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "NeoMakerViGate v0.1.0"
            font.pixelSize: 28
            color: "#C77B2C"
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "Maker Việt × Dế Foundation"
            font.pixelSize: 18
            color: "#3F6627"
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }
        Item { height: 20 }
        BusyIndicator {
            Layout.alignment: Qt.AlignHCenter
            running: true
        }
    }

    Timer {
        interval: 2000
        running: true
        repeat: false
        onTriggered: splash.splashDone()
    }
}
