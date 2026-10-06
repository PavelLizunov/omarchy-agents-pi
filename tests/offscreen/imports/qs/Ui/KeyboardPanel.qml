import QtQuick
import qs.Commons

Item {
  id: root
  property Item anchorItem: null
  property QtObject bar: null
  property var owner: null
  property int margin: Style.gapsOut
  property int padding: Style.spacing.popupPadding
  property int contentWidth: Style.space(280)
  property int contentHeight: Style.space(200)
  property var borderSpec: Border.surfaceSpec("popups", "border", Color.popups.border, Math.max(1, Style.space(2)))
  property bool centerOnBar: false
  property bool open: true
  property int gap: Style.gapsOut
  property bool popoutSwitching: false
  property bool popoutSwitchClosing: false
  property bool focusPrimed: false
  property Item focusTarget: null

  width: contentWidth
  height: contentHeight

  function fittedContentWidth(w) { return w }
  function fittedContentHeight(h, cap) {
    var wanted = h + padding * 2 + Border.top(borderSpec) + Border.bottom(borderSpec)
    return cap > 0 ? Math.min(wanted, cap) : wanted
  }
  function close() {}

  BorderSurface {
    id: card
    anchors.fill: parent
    color: Color.popups.background
    borderSpec: root.borderSpec
    padding: root.padding
    radius: Style.cornerRadius

    Item {
      id: contentHolder
      anchors.fill: parent
      anchors.topMargin: card.contentTopInset
      anchors.rightMargin: card.contentRightInset
      anchors.bottomMargin: card.contentBottomInset
      anchors.leftMargin: card.contentLeftInset
    }
  }

  default property alias contentItem: contentHolder.children
}
