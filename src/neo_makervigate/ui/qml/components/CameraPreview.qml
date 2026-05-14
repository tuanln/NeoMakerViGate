import QtQuick

// Hiển thị frame webcam từ CameraImageProvider.
// Tự refresh ~30fps qua timer bumps VisionState.previewCounter.
Item {
    id: root

    // Override để tắt refresh nếu cần
    property bool active: true
    property real refreshMs: 33

    Image {
        id: previewImage
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        cache: false           // luôn fetch lại
        smooth: true
        asynchronous: false
        // Bust cache bằng counter — QML nhận biết property thay đổi và refetch
        source: "image://camera/preview?bust=" + counter
        property int counter: 0
    }

    Timer {
        interval: root.refreshMs
        running: root.active
        repeat: true
        onTriggered: previewImage.counter++
    }
}
