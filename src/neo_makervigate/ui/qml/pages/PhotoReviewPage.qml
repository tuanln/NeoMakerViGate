import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../singletons" as Sing

Item {
    id: page

    signal backRequested()

    readonly property var result: app.photoResult
    readonly property string qrPath: result && result.qr_path ? result.qr_path : ""
    readonly property string downloadUrl: result && result.download_url ? result.download_url : ""
    readonly property string originalPath: result && result.original_path ? result.original_path : ""

    Rectangle {
        anchors.fill: parent
        color: Sing.NeoConstants.background
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 32

        // Left: original photo
        Item {
            Layout.fillHeight: true
            Layout.preferredWidth: parent.width * 0.55
            Image {
                anchors.fill: parent
                source: page.originalPath ? "file://" + page.originalPath : ""
                fillMode: Image.PreserveAspectFit
                cache: false
            }
        }

        // Right: QR + instructions + back
        ColumnLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: 20

            Text {
                text: "📸 Đã chụp xong!"
                font.pixelSize: 36
                font.bold: true
                color: Sing.NeoConstants.tre
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: "Ba mẹ ơi, quét mã bằng Zalo\nđể tải ảnh về điện thoại!"
                font.pixelSize: 22
                color: Sing.NeoConstants.de
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }

            // QR image
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 360
                Layout.preferredHeight: 360
                color: "white"
                border.color: Sing.NeoConstants.tre
                border.width: 2
                Image {
                    anchors.fill: parent
                    anchors.margins: 8
                    source: page.qrPath ? "file://" + page.qrPath : ""
                    fillMode: Image.PreserveAspectFit
                    cache: false
                }
            }

            Text {
                text: page.downloadUrl
                font.pixelSize: 14
                color: Sing.NeoConstants.textPrimary
                opacity: 0.6
                wrapMode: Text.WrapAnywhere
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }

            Item { Layout.fillHeight: true }

            // Back button
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 240
                Layout.preferredHeight: 64
                radius: 32
                color: Sing.NeoConstants.tre
                Text {
                    anchors.centerIn: parent
                    text: "← Về Hub"
                    color: "white"
                    font.pixelSize: 24
                    font.bold: true
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: page.backRequested()
                }
            }
        }
    }
}
