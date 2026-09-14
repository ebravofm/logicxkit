on run argv
  set targetName to item 1 of argv
  tell application "System Events" to tell process "Logic Pro"
    set frontmost to true
    set w to window 1
    set els to entire contents of w
    set hits to {}
    repeat with e in els
      try
        set r to role of e
        if r is "AXCheckBox" or r is "AXButton" then
          set n to name of e
          if n is missing value then set n to description of e
          if (n as text) is targetName then set end of hits to e
        end if
      end try
    end repeat
    if (count of hits) is 0 then return "NOTFOUND"
    set e to item 1 of hits
    set v0 to ""
    try
      set v0 to (value of e) as text
    end try
    perform action "AXPress" of e
    delay 0.5
    set v1 to ""
    try
      set v1 to (value of e) as text
    end try
    return (count of hits) & " hit(s): " & v0 & "->" & v1
  end tell
end run
