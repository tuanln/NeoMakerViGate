import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../singletons" as Sing

// Thẻ trong lưới Hub. Tap → emit selected(expId).
Rectangle {
    id: card

    property string expId: ""
    property string title: ""
    property string subtitle: ""
    property int ageMin: 0
    property int ageMax: 14
    property bool needsQwen: false
    property bool needsInternet: false

    signal selected(string id)

    width: Sing.NeoConstants.cardWidth
    height: Sing.NeoConstants.cardHeight
    radius: 16
    color: Sing.NeoConstants.surface
    border.color: Sing.NeoConstants.tre
    border.width: 2

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 8

        Text {
            text: card.title
            font.pixelSize: 26
            font.bold: true
            color: Sing.NeoConstants.tre
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Text {
            text: card.subtitle
            font.pixelSize: 16
            color: Sing.NeoConstants.de
            font.italic: true
            Layout.fillWidth: true
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            spacing: 8
            Layout.fillWidth: true

            Rectangle {
                visible: card.needsQwen
                radius: 8
                color: Sing.NeoConstants.song
                Layout.preferredWidth: childrenRect.width + 16
                Layout.preferredHeight: 22
                Text {
                    text: "AI"
                    color: "white"
                    font.pixelSize: 12
                    font.bold: true
                    anchors.centerIn: parent
                }
            }
            Rectangle {
                visible: card.needsInternet
                radius: 8
                color: Sing.NeoConstants.gach
                Layout.preferredWidth: childrenRect.width + 16
                Layout.preferredHeight: 22
                Text {
                    text: "Wifi"
                    color: "white"
                    font.pixelSize: 12
                    font.bold: true
                    anchors.centerIn: parent
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: card.ageMin + "-" + card.ageMax + " tuổi"
                font.pixelSize: 14
                color: Sing.NeoConstants.textPrimary
                opacity: 0.7
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: card.selected(card.expId)
    }

    states: State {
        when: cardHover.containsMouse
        PropertyChanges {
            target: card
            border.width: 4
            color: Sing.NeoConstants.background
        }
    }

    MouseArea {
        id: cardHover
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    Behavior on border.width { NumberAnimation { duration: Sing.NeoConstants.animFast } }
}
