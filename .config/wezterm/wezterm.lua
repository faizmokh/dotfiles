local wezterm = require 'wezterm'
local fish = '/opt/homebrew/bin/fish'

local function directory(pane)
    local cwd = pane:get_current_working_dir()
    -- Only use local file URLs; a remote pane's directory may not exist locally.
    if cwd and cwd.file_path and (not cwd.host or cwd.host == '' or cwd.host == wezterm.hostname()) then
        return cwd.file_path
    end
    return wezterm.home_dir
end

local function launch(command, with_git)
    return function(window, pane)
        local cwd = directory(pane)
        local _, new_pane = window:mux_window():spawn_tab {
            cwd = cwd,
            domain = 'DefaultDomain',
            -- Interactive startup activates mise; commands are fixed literals.
            args = { fish, '-lic', command },
        }
        if with_git then
            local success, stdout = wezterm.run_child_process {
                '/usr/bin/git', '-C', cwd, 'rev-parse', '--is-inside-work-tree',
            }
            if success and stdout:match('^true') then
                new_pane:split {
                    direction = 'Right', size = 0.5, cwd = cwd,
                    args = { fish, '-lic', 'lazygit' },
                }
            end
        end
    end
end

wezterm.on('opencode-and-lazygit', launch('opencode', true))
wezterm.on('pi-and-lazygit', launch('pi', true))
wezterm.on('lazygit', launch('lazygit', false))

return {
    default_prog = { fish, '-l' },
    color_scheme = 'Dracula (Official)',
    font = wezterm.font_with_fallback { 'Maple Mono' },
    font_size = 14.0,
    line_height = 1.0,
    window_decorations = 'RESIZE',
    enable_tab_bar = true,
    hide_tab_bar_if_only_one_tab = true,
    use_fancy_tab_bar = false,
    tab_bar_at_bottom = true,
    window_frame = { font = wezterm.font_with_fallback { 'Maple Mono' } },
    keys = {
        { key = 'd', mods = 'CMD|SHIFT', action = wezterm.action.SplitHorizontal { domain = 'CurrentPaneDomain' } },
        { key = 'd', mods = 'CMD', action = wezterm.action.SplitVertical { domain = 'CurrentPaneDomain' } },
        { key = 'w', mods = 'CMD', action = wezterm.action.CloseCurrentPane { confirm = true } },
        { key = 'w', mods = 'CMD|SHIFT', action = wezterm.action.CloseCurrentTab { confirm = true } },
        { key = 'Enter', mods = 'CMD', action = wezterm.action.ToggleFullScreen },
        { key = 'g', mods = 'CMD|SHIFT', action = wezterm.action.EmitEvent 'lazygit' },
        { key = 'o', mods = 'CMD|SHIFT', action = wezterm.action.EmitEvent 'opencode-and-lazygit' },
        { key = 'p', mods = 'CMD|SHIFT', action = wezterm.action.EmitEvent 'pi-and-lazygit' },
    },
}
