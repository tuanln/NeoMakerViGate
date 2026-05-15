import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../singletons" as Sing

// Hub — lưới các thẻ trải nghiệm. P2 hiện 3 thẻ stub (MVP scope).
// QML đọc app.experienceMetas (list of dict từ AppController).
Item {
    id: page

    signal experienceChosen(string id)

    Rectangle {
        anchors.fill: parent
        color: Sing.NeoConstants.background
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 20

        // Header
        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 4
            Text {
                text: "Cổng Làng Maker"
                font.pixelSize: Sing.NeoConstants.fontTitle
                font.bold: true
                color: Sing.NeoConstants.tre
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Chọn một trò chơi để bắt đầu"
                font.pixelSize: 22
                color: Sing.NeoConstants.de
                Layout.alignment: Qt.AlignHCenter
            }
        }

        // Lưới thẻ — Flow wrap responsive
        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentHeight: flow.implicitHeight
            clip: true

            Flow {
                id: flow
                width: parent.width
                spacing: 24
                anchors.horizontalCenter: parent.horizontalCenter

                Repeater {
                    model: app.experienceMetas
                    ExperienceCard {
                        expId: modelData.id
                        title: modelData.title
                        subtitle: modelData.subtitle
                        ageMin: modelData.ageMin
                        ageMax: modelData.ageMax
                        needsQwen: modelData.needsQwen
                        needsInternet: modelData.needsInternet
                        onSelected: function(id) { page.experienceChosen(id) }
                    }
                }
            }
        }

        // Footer
        Text {
            text: "v0.1.0 — MVP 3 trải nghiệm | Maker Việt × Dế Foundation"
            font.pixelSize: 14
            color: Sing.NeoConstants.textPrimary
            opacity: 0.5
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
