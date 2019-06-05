-- Variables

local hyper = {"ctrl", "alt", "cmd"}
local power = {"ctrl", "cmd"}

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

-- Listen to wifi events

wifiwatcher = hs.wifi.watcher.new(function ()
  net = hs.wifi.currentNetwork()
  if net==nil then
      hs.notify.show("You lost Wi-Fi connection","","","")
  else
      hs.notify.show("Connected to Wi-Fi network","",net,"")
  end
end)
wifiwatcher:start()

-- Quick open applications

function open(name)
  return function()
      hs.application.launchOrFocus(name)
      if name == 'Finder' then
          hs.appfinder.appFromName(name):activate()
      end
  end
end

hs.hotkey.bind(power, "X", open("Xcode"))
hs.hotkey.bind(power, "I", open("iTerm"))

-- Quick switch Chrome users

function chrome_switch_to(user)
  return function()
      hs.application.launchOrFocus("Google Chrome")
      local chrome = hs.appfinder.appFromName("Google Chrome")
      local str_menu_item
      if user == "Incognito" then
          str_menu_item = {"File", "New Incognito Window"}
      else
          str_menu_item = {"People", user}
      end
      local menu_item = chrome:findMenuItem(str_menu_item)
      if (menu_item) then
          chrome:selectMenuItem(str_menu_item)
      end
  end
end

hs.hotkey.bind(power, "1", chrome_switch_to("Personal"))
hs.hotkey.bind(power, "2", chrome_switch_to("Work"))
hs.hotkey.bind(power, "3", chrome_switch_to("Incognito"))

-- Autoreload configurations

spoon.ReloadConfiguration:start()