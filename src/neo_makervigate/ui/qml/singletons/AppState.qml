pragma Singleton
import QtQuick

// Global UI state — bind từ AppController. KHÔNG dùng làm source of truth,
// chỉ mirror để các page bên trong dùng tiện hơn `app.currentExperience`.
QtObject {
    property string currentExperience: ""
    property string status: "idle"  // idle | hub | playing | reviewing
    property int score: 0
    property real progress: 0.0
}
