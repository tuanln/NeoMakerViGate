pragma Singleton
import QtQuick

QtObject {
    // P1: cờ kết nối + counter để bust cache cho CameraPreview.Image
    property bool cameraConnected: false
    property int previewCounter: 0
    property real visionFps: 0.0

    // P1 landmarks — Python push qua AppController.update_vision_state()
    // hands: [ [ {x,y}, ... 21 pts ], ... ] | pose: [ {x,y,visibility}, ... 33 ] | face: [{x,y}, ...]
    property var poseLandmarks: []
    property var handLandmarks: []
    property var faceLandmarks: []

    // Cử chỉ gần nhất từ GestureDetector (P3+)
    property string lastGesture: ""
}
