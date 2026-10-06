import QtQuick
Item {
  property string path: ""
  property bool watchChanges: false
  property bool atomicWrites: false
  function setText(value) { throw new Error("Unexpected filesystem write"); }
  property bool printErrors: false
  signal loaded()
  signal loadFailed()
  signal fileChanged()
  function reload() {}
  function text() { return ""; }
}
