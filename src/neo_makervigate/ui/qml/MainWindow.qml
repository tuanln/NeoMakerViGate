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
    color: "#FAF6EE"

    StackView {
        id: stack
        anchors.fill: parent
        initialItem: splashComponent
    }

    Component {
        id: splashComponent
        SplashScreen {
            onSplashDone: stack.replace(hubComponent)
        }
    }

    Component {
        id: hubComponent
        ExperienceHubPage {
            onExperienceChosen: function(id) {
                if (app.selectExperience(id)) {
                    stack.push(containerComponent)
                }
            }
        }
    }

    Component {
        id: containerComponent
        ExperienceContainerPage {
            onBackRequested: {
                app.exitExperience()
                stack.pop()
            }
        }
    }
}
