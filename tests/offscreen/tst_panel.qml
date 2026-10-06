import QtQuick
import QtQuick.Window
import QtTest
import qs.Commons
import "consumer" as Agents

Item {
  id: host
  width: 440
  height: 720

  QtObject {
    id: inertBar
    property color foreground: Color.foreground
    property color barForeground: Color.foreground
    property color urgent: Color.urgent
    property string fontFamily: Style.font.family
    property bool vertical: false
    property bool foregroundAnimationEnabled: false
    property int barSize: 32
    function run(command) { throw new Error("Unexpected command"); }
    function hideTooltip(item) {}
    function showTooltip(item, text) {}
  }

  Component {
    id: panelComponent
    Agents.Panel {
      x: 20
      y: 20
      width: 380
      height: 32
      bar: inertBar
    }
  }

  TestCase {
    name: "PiDailyCachePanel"
    when: windowShown
    property var panel: null
    property string outputDir: "@OUTPUT_DIR@"

    function init() { panel = panelComponent.createObject(host); verify(panel !== null) }
    function cleanup() { panel.destroy(); panel = null; wait(0) }

    function find(item, predicate) {
      if (predicate(item)) return item
      var children = item.children || []
      for (var i = 0; i < children.length; ++i) {
        var found = find(children[i], predicate)
        if (found) return found
      }
      return null
    }

    function record(id, name, tier, input, cached) {
      return {id: id, name: name, tierLabel: tier, ready: true,
        totalPrompts: 3, totalSessions: 1, activeDays: 1,
        todayPrompts: 3, todaySessions: 1, limits: [],
        recentDays: [
          {date: "2026-09-28", messageCount: 0, cacheHitRate: null},
          {date: "2026-09-29", messageCount: 2000, cacheHitRate: 0},
          {date: "2026-09-30", messageCount: 3000, cacheHitRate: 1},
          {date: "2026-10-01", messageCount: 2000, cacheHitRate: 0.9361},
          {date: "2026-10-02", messageCount: 5000, cacheHitRate: 0.4189},
          {date: "2026-10-03", messageCount: 1000, cacheHitRate: 0.8064},
          {date: "2026-10-04", messageCount: 4000, cacheHitRate: 0.8262}],
        modelUsage: {"fixture-model": {inputTokens: input, outputTokens: 20,
          cacheReadInputTokens: cached, cacheCreationInputTokens: 0}}}
    }

    function capture(item, path) {
      var saved = false
      verify(item.grabToImage(function(result) { saved = result.saveToFile(path) }))
      tryVerify(function() { return saved })
    }

    function test_cache_contract() {
      compare(panel.cacheHitText(null), "—")
      compare(panel.cacheHitText({cacheHitRate: 0}), "0.0%")
      compare(panel.cacheHitText({cacheHitRate: 1}), "100.0%")
      compare(panel.cacheHitText({cacheHitRate: 0.9361}), "93.6%")
      for (var value of [-1, 2, NaN, Infinity, "0.5", true, null, undefined])
        compare(panel.cacheHitText({cacheHitRate: value}), "—")
      compare(panel.iconCandidatesForProvider({providerId: "pi"}, "#ffffff").length, 1)
      verify(String(panel.iconCandidatesForProvider({providerId: "pi"}, "#ffffff")[0]).endsWith("/assets/pi.svg"))
    }

    function test_provider_order_and_clicks() {
      var usage = find(panel, function(x) { return typeof x.displayProvider === "function"; })
      verify(usage !== null)
      var a = {record: record("claude", "Claude Code", "Max", 100, 200)}
      var b = {record: record("codex", "Codex", "Pro", 100, 200)}
      var c = {record: record("opencode", "OpenCode", "Plan", 100, 200)}
      var p = {record: record("pi", "Pi", "All-time cache hit 90.0%", 10, 90)}
      for (var order of [[p,a,b,c], [a,p,b,c], [a,b,p,c], [a,b,c,p]]) {
        usage.settings = ({})
        usage.agents = order
        usage.recordsChanged()
        compare(panel.providers.map(function(x) { return x.providerId; }).join(","), "pi,claude,codex,opencode")
      }
      usage.settings = ({providers: {pi: {enabled: false}}})
      usage.recordsChanged()
      compare(panel.providers.map(function(x) { return x.providerId; }).join(","), "claude,codex,opencode")
      usage.settings = ({})
      usage.recordsChanged()
      panel.selectedProviderId = ""
      panel.close()
      var button = find(panel, function(x) { return typeof x.triggerPress === "function"; })
      verify(button !== null)
      mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton)
      tryCompare(panel, "opened", true)
      mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton)
      tryCompare(panel, "opened", false)
      mouseClick(button, button.width / 2, button.height / 2, Qt.MiddleButton)
      compare(panel.provider.providerId, "claude")
      panel.selectProvider(-1)
      compare(panel.provider.providerId, "opencode")
      panel.selectProvider(0)
      usage.agents = [a,p,b,c]
      usage.recordsChanged()
      compare(panel.provider.providerId, "pi")
      panel.close()
    }

    function test_missing_icon_then_pi() {
      test_provider_order_and_clicks()
      wait(0)
      compare(panel.provider.providerId, "pi")
      var hero = find(panel, function(x) { return x.candidatesKey !== undefined; })
      verify(hero !== null)
      console.log("Icon regression:", hero.candidatesKey, "index", hero.candidateIndex,
                  "count", hero.candidates.length)
      tryVerify(function() {
        var image = find(panel, function(x) {
          return x.source !== undefined && String(x.source).endsWith("/pi.svg")
        })
        return image !== null && image.status === Image.Ready
      }, 1000, "Pi icon must recover after a missing previous icon")
      panel.open()
      var card = find(panel, function(x) { return x.contentWidth !== undefined && x.focusTarget !== undefined; })
      verify(card !== null)
      wait(200)
      capture(card, outputDir + "/pi-after-missing-icon.png")
    }

    function test_same_provider_fallback() {
      var usage = find(panel, function(x) { return typeof x.displayProvider === "function"; })
      usage.agents = [{record: record("pi", "Pi", "Cache", 10, 90)}]
      usage.recordsChanged()
      var hero = find(panel, function(x) { return x.candidatesKey !== undefined; })
      verify(hero !== null)
      var piSource = hero.candidates[0]
      hero.candidates = [Qt.resolvedUrl("consumer/assets/missing-fixture.svg"), piSource]
      tryCompare(hero, "candidateIndex", 1)
      tryVerify(function() {
        var image = find(panel, function(x) {
          return x.source !== undefined && String(x.source).endsWith("/pi.svg")
        })
        return image !== null && image.status === Image.Ready
      })
    }

    function test_states() {
      panel.Window.window.width = 440
      panel.Window.window.height = 720
      var usage = find(panel, function(x) { return typeof x.displayProvider === "function"; })
      verify(usage !== null)
      usage.agents = [
        {record: record("claude", "Claude Code", "Max", 100, 200)},
        {record: record("codex", "Codex", "Pro", 100, 200)},
        {record: record("opencode", "OpenCode", "Ninitux AI", 100, 200)},
        {record: record("pi", "Pi", "All-time cache hit 90.0%", 10, 90)}]
      usage.recordsChanged()
      panel.selectedProviderId = ""
      panel.open()
      tryCompare(panel, "opened", true)
      compare(panel.providers.map(function(p) { return p.providerId; }).join(","), "pi,claude,codex,opencode")
      compare(panel.provider.providerId, "pi")
      compare(panel.heroMeta(panel.provider), "All-time cache hit 90.0%")
      var card = find(panel, function(x) { return x.contentWidth !== undefined && x.focusTarget !== undefined; })
      verify(card !== null)
      var image = find(card, function(x) { return x.source !== undefined && String(x.source).endsWith("/pi.svg"); })
      verify(image !== null)
      tryCompare(image, "status", Image.Ready)
      wait(200)
      capture(card, outputDir + "/pi-daily-panel.png")
      var meta = find(card, function(x) { return x.text === "ALL-TIME CACHE HIT 90.0%"; })
      verify(meta !== null)
      verify(meta.implicitWidth <= meta.width, "Cache label is clipped")
      var cache = find(card, function(x) { return x.objectName === "dayCache-2026-09-30"; })
      verify(cache !== null)
      compare(cache.text, "100.0%")
      verify(cache.implicitWidth <= cache.width, "Daily 100% label is clipped")
      compare(find(card, function(x) { return x.objectName === "dayCache-2026-09-29"; }).text, "0.0%")
      compare(find(card, function(x) { return x.objectName === "dayCache-2026-09-28"; }).text, "—")
      compare(find(card, function(x) { return x.objectName === "dayCache-2026-10-04"; }).text, "82.6%")
      var key = find(card, function(x) { return x.moveRequested !== undefined; })
      verify(key !== null)
      key.moveRequested(1, 0)
      compare(panel.provider.providerId, "claude")
      verify(!find(card, function(x) { return x.objectName === "dayCache-2026-09-30"; }).visible)
      wait(50)
      capture(card, outputDir + "/claude-preserved.png")
      key.moveRequested(-1, 0)
      compare(panel.provider.providerId, "pi")
      usage.agents[3].record.tierLabel = "All-time cache hit 100.0%"
      usage.recordsChanged()
      wait(200)
      compare(panel.heroMeta(panel.provider), "All-time cache hit 100.0%")
      capture(card, outputDir + "/pi-daily-panel-100.png")
      meta = find(card, function(x) { return x.text === "ALL-TIME CACHE HIT 100.0%"; })
      verify(meta !== null)
      verify(meta.implicitWidth <= meta.width, "100% label is clipped")
      usage.agents[3].record.tierLabel = "All-time cache hit —"
      usage.agents[3].record.recentDays = usage.agents[3].record.recentDays.map(function(day) {
        return {date: day.date, messageCount: day.messageCount, cacheHitRate: null};
      })
      usage.recordsChanged()
      wait(200)
      capture(card, outputDir + "/pi-daily-panel-unavailable.png")
      compare(panel.heroMeta(panel.provider), "All-time cache hit —")
      compare(find(card, function(x) { return x.objectName === "dayCache-2026-09-30"; }).text, "—")
      key.closeRequested()
      compare(panel.opened, false)
    }
  }
}
