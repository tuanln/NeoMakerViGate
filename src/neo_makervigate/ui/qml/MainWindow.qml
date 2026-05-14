import QtQuick
import QtQuick.Controls
import QtQuick.Window
import "pages"

ApplicationWindow {
    id: window
    visible: true
    width: 1280
    height: 800
    title: qsTr("NeoMakerViGate — Cổng Vào Làng Maker")

    // Palette Dế Foundation
    readonly property color treBg: "#FAF6EE"
    readonly property color treFg: "#5C8A3A"
    readonly property color deFg: "#C77B2C"

    color: treBg

    StackView {
        id: stack
        anchors.fill: parent
        initialItem: splashComponent
    }

    Component {
        id: splashComponent
        SplashScreen {
            onSplashDone: {
                // Phase 0: tự đóng app sau splash để verify pipeline.
                // Phase 2 sẽ push(hubPage) thay vào đây.
                Qt.quit()
            }
        }
    }
}
