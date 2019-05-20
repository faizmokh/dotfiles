-- Variables

local hyper = {"ctrl", "alt", "cmd"}

-- Spoons

hs.loadSpoon("MiroWindowsManager")
hs.loadSpoon("ReloadConfiguration")

-- Windows manager

hs.window.animationDuration = 0.2
spoon.MiroWindowsManager:bindHotkeys({
  up = {hyper, "up"},
  right = {hyper, "right"},
  down = {hyper, "down"},
  left = {hyper, "left"},
  fullscreen = {hyper, "f"}
})

-- Avoid paste blocking

hs.hotkey.bind(hyper, "V", function() hs.eventtap.keyStrokes(hs.pasteboard.getContents()) end)

spoon.ReloadConfiguration:start()