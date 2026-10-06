import QtQuick
pragma Singleton
QtObject {
  function env(k) {
    if (k === "HOME") return "/inert-fixture-home";
    if (k === "USER") return "fixture";
    return "";
  }
  function execDetached(cmd) { throw new Error("Unexpected detached process"); }
}
