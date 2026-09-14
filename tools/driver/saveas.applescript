on run argv
  set newName to item 1 of argv
  if (count of argv) < 2 then return "USAGE: saveas.applescript <name> <absolute save folder>"
  set destDir to item 2 of argv
  tell application "System Events" to tell process "Logic Pro"
    set frontmost to true
    delay 1
    if (count of windows) is 0 then return "NO DOCUMENT"
    perform action "AXRaise" of window 1
    delay 0.5
    keystroke "s" using {command down, shift down}
    set waited to 0
    repeat until (exists window "Save") or waited > 10
      delay 0.5
      set waited to waited + 0.5
    end repeat
    if not (exists window "Save") then return "NO SAVE DIALOG"
    delay 2
    keystroke "a" using command down
    delay 0.5
    keystroke newName
    delay 1
    keystroke "g" using {command down, shift down}
    delay 2
    keystroke destDir
    delay 1
    key code 36
    delay 2
    key code 36
    delay 8
    return (name of every window) as text
  end tell
end run
