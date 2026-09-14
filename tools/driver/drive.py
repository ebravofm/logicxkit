"""Measure project state: one action, one Save As, per step. Steps come from steps.json.

    python3 tools/driver/drive.py steps.json <first number>

Saves land in `LOGIC_SAVE_DIR` (default: the repo's `out/scratch`) as
`CLAUDE <LOGIC_SAVE_PREFIX> <number> <label> (Logic save).logicx`; `tools/driver/README.md`
has the loop and the traps.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
OUT = os.environ.get("LOGIC_SAVE_DIR", str(HERE.parents[1] / "out" / "scratch"))
PREFIX = os.environ.get("LOGIC_SAVE_PREFIX", "modes")   # the family name in every save's file name


def osa(script, *args):
    r = subprocess.run(["osascript", "-", *args], input=script, capture_output=True, text=True, timeout=180)
    return ("ERROR " + r.stderr.strip()) if r.returncode else r.stdout.strip()


SAVEAS = (HERE / "saveas.applescript").read_text()

BAR = '''
on run argv
  set targetName to item 1 of argv
  tell application "System Events" to tell process "Logic Pro"
    set frontmost to true
    set g to missing value
    repeat with e in UI elements of window 1
      try
        if role of e is "AXGroup" and description of e is "Control Bar" then set g to e
      end try
    end repeat
    if g is missing value then return "NOTFOUND (no control bar group)"
    repeat with e in UI elements of g
      try
        if (name of e as text) is targetName then
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
          return v0 & "->" & v1
        end if
      end try
    end repeat
    return "NOTFOUND"
  end tell
end run
'''

MENU = '''
on run argv
  tell application "System Events" to tell process "Logic Pro"
    set frontmost to true
    delay 0.5
    set m to menu (item 1 of argv) of menu bar item (item 1 of argv) of menu bar 1
    if (count of argv) is 2 then
      click menu item (item 2 of argv) of m
    else
      click menu item (item 3 of argv) of menu 1 of menu item (item 2 of argv) of m
    end if
    delay 1
    return "clicked"
  end tell
end run
'''

SETTINGS = '''
on run argv
  set pane to item 1 of argv
  set mode to item 2 of argv
  set targetRole to item 3 of argv
  set targetName to item 4 of argv
  set nth to (item 5 of argv) as integer
  set arg to item 6 of argv
  tell application "System Events" to tell process "Logic Pro"
    set frontmost to true
    set w to missing value
    repeat with x in windows
      if (name of x as text) contains "Project Settings" then set w to x
    end repeat
    set attempt to 0
    repeat while w is missing value and attempt < 4
      set attempt to attempt + 1
      try
        click menu item (pane & "…") of menu 1 of menu item "Project Settings" of menu "File" of menu bar item "File" of menu bar 1
      end try
      set waited to 0
      repeat while w is missing value and waited < 6
        delay 0.5
        set waited to waited + 0.5
        repeat with x in windows
          if (name of x as text) contains "Project Settings" then set w to x
        end repeat
      end repeat
    end repeat
    if w is missing value then return "ERROR no Project Settings window after " & attempt & " tries"
    repeat with t in UI elements of w
      try
        if role of t is "AXToolbar" then perform action "AXPress" of button pane of t
      end try
    end repeat
    delay 1
    if mode is "close" then
      perform action "AXPress" of (first button of w whose subrole is "AXCloseButton")
      delay 1
      return "closed"
    end if
    set found to {}
    repeat with e in UI elements of w
      try
        if role of e is targetRole then
          set n to name of e
          if n is missing value then set n to description of e
          if (n as text) is targetName then set end of found to e
        else if role of e is "AXGroup" then
          repeat with f in UI elements of e
            try
              if role of f is targetRole then
                set n to name of f
                if n is missing value then set n to description of f
                if (n as text) is targetName then set end of found to f
              end if
            end try
          end repeat
        end if
      end try
    end repeat
    if (count of found) < nth then
      perform action "AXPress" of (first button of w whose subrole is "AXCloseButton")
      return "NOTFOUND (" & (count of found) & " named " & targetName & ")"
    end if
    set e to item nth of found
    set v0 to ""
    try
      set v0 to (value of e) as text
    end try
    if mode is "press" then
      perform action "AXPress" of e
    else if mode is "increment" then
      perform action "AXIncrement" of e
    else if mode is "decrement" then
      perform action "AXDecrement" of e
    else if mode is "choose" then
      perform action "AXPress" of e
      delay 0.4
      click menu item arg of menu 1 of e
    else if mode is "setvalue" then
      set value of e to (arg as number)
    else if mode is "locate" then
      set p to position of e
      set z to size of e
      return ((item 1 of p) as text) & "," & ((item 2 of p) as text) & "," & ((item 1 of z) as text) & "," & ((item 2 of z) as text) & "," & v0
    end if
    delay 0.5
    set v1 to ""
    try
      set v1 to (value of e) as text
    end try
    perform action "AXPress" of (first button of w whose subrole is "AXCloseButton")
    delay 1
    return v0 & "->" & v1
  end tell
end run
'''

POPOVER = '''
on run argv
  -- argv: menuBarItem, menuItem, [submenuItem or ""], targetRole, targetName
  set barItem to item 1 of argv
  set menuName to item 2 of argv
  set subName to item 3 of argv
  set targetRole to item 4 of argv
  set targetNames to items 5 thru -1 of argv
  tell application "System Events" to tell process "Logic Pro"
    set frontmost to true
    delay 0.5
    set m to menu barItem of menu bar item barItem of menu bar 1
    set attempt to 0
    set pop to missing value
    repeat while pop is missing value and attempt < 4
      set attempt to attempt + 1
      try
        if subName is "" then
          click menu item menuName of m
        else
          click menu item subName of menu 1 of menu item menuName of m
        end if
      end try
      set waited to 0
      repeat while pop is missing value and waited < 5
        delay 0.5
        set waited to waited + 0.5
        repeat with e in UI elements of window 1
          try
            if role of e is "AXPopover" then set pop to e
          end try
        end repeat
      end repeat
    end repeat
    if pop is missing value then return "ERROR no popover after " & attempt & " tries"
    set report to ""
    repeat with targetName in targetNames
      set found to missing value
      repeat with e in entire contents of pop
        try
          if role of e is targetRole then
            set n to name of e
            if n is missing value then set n to description of e
            if (n as text) is (targetName as text) then set found to e
          end if
        end try
      end repeat
      if found is missing value then
        key code 53
        return "NOTFOUND (" & targetName & " in popover)"
      end if
      set v0 to ""
      try
        set v0 to (value of found) as text
      end try
      perform action "AXPress" of found
      delay 0.4
      set v1 to ""
      try
        set v1 to (value of found) as text
      end try
      set report to report & targetName & " " & v0 & "->" & v1 & "; "
    end repeat
    key code 53
    delay 1
    return report
  end tell
end run
'''


ESCAPE = 'tell application "System Events" to tell process "Logic Pro" to key code 53'


SHEET = '''
on run argv
  -- argv: radioName (or ""), buttonName; acts on the first sheet of window 1
  set radioName to item 1 of argv
  set buttonName to item 2 of argv
  tell application "System Events" to tell process "Logic Pro"
    set frontmost to true
    set sh to missing value
    set waited to 0
    repeat while sh is missing value and waited < 8
      repeat with e in UI elements of window 1
        try
          if role of e is "AXSheet" then set sh to e
        end try
      end repeat
      if sh is missing value then
        delay 0.5
        set waited to waited + 0.5
      end if
    end repeat
    if sh is missing value then return "ERROR no sheet"
    set report to ""
    if radioName is not "" then
      set hit to missing value
      repeat with e in UI elements of sh
        try
          if role of e is "AXRadioButton" and (name of e as text) is radioName then set hit to e
        end try
      end repeat
      if hit is missing value then return "NOTFOUND (radio " & radioName & ")"
      perform action "AXPress" of hit
      delay 0.5
      set report to radioName & " pressed; "
    end if
    set btn to missing value
    repeat with e in UI elements of sh
      try
        if role of e is "AXButton" and (name of e as text) is buttonName then set btn to e
      end try
    end repeat
    if btn is missing value then return "NOTFOUND (button " & buttonName & ")"
    perform action "AXPress" of btn
    delay 2
    return report & buttonName & " pressed"
  end tell
end run
'''


CLOSE_SETTINGS = '''
tell application "System Events" to tell process "Logic Pro"
  repeat with x in windows
    if (name of x as text) contains "Project Settings" then
      perform action "AXPress" of (first button of x whose subrole is "AXCloseButton")
    end if
  end repeat
end tell
'''


def drag_control(step):
    """Locate a Project Settings control, drag it by (dx, dy) with a real mouse, close the pane."""
    r = osa(SETTINGS, step["pane"], "locate", step.get("role", "AXSlider"), step["name"],
            str(step.get("nth", 1)), "")
    if r.startswith("ERROR") or r.startswith("NOTFOUND"):
        return r
    x, y, w, h, v0 = r.split(",")
    cx, cy = float(x) + float(w) / 2, float(y) + float(h) / 2
    dx, dy = step.get("by", [0, -10])
    subprocess.run([*tool("drag"), str(cx), str(cy), str(cx + dx), str(cy + dy)], timeout=60)
    time.sleep(1)
    osa(CLOSE_SETTINGS)
    time.sleep(1)
    return f"dragged from {v0} at ({cx:.0f},{cy:.0f}) by ({dx},{dy})"


def tool(name):
    """A compiled helper under scripts/bin/ when present (swiftc -O), else the script via swift."""
    built = HERE / "bin" / name
    return [str(built)] if built.exists() else ["swift", str(HERE / f"{name}.swift")]


def popover_origin():
    """(x, y) of the unnamed layer-0 window a popover opens as, or None."""
    r = subprocess.run(tool("winids-all"), capture_output=True, text=True, timeout=60)
    for line in r.stdout.splitlines():
        parts = [x.strip() for x in line.split("|")]
        if len(parts) == 4 and parts[1] == "0" and parts[2] == "":   # untitled: the main window has a title
            x, y, w, h = parts[3].split()
            return int(x), int(y)
    return None


KEYS = '''
on run argv
  tell application "System Events" to tell process "Logic Pro"
    repeat with k in argv
      if (k as text) is "Return" then
        key code 36
      else
        keystroke (k as text)
      end if
      delay 0.6
    end repeat
  end tell
end run
'''


def click_popover(path, clicks, keys=()):
    """Open a popover through a menu path, click each (dx, dy) inside it — a popup's menu is
    then chosen by typing ``keys`` (type-select, then Return) — and Escape closes it."""
    r = osa(MENU, *path)
    if r.startswith("ERROR"):
        return r
    time.sleep(2)
    origin = popover_origin()
    if origin is None:
        return "ERROR no popover window"
    for dx, dy in clicks:
        subprocess.run([*tool("click"), str(origin[0] + dx), str(origin[1] + dy)], timeout=60)
        time.sleep(1)
    if keys:
        osa(KEYS, *keys)
        time.sleep(1)
    osa(ESCAPE)
    time.sleep(1)
    return f"clicked popover@{origin} {clicks}" + (f" keys={list(keys)}" if keys else "")


def main(steps_file, start_at):
    steps = json.loads(Path(steps_file).read_text())
    log = open(HERE / "drive.log", "a")
    n = start_at
    for step in steps:
        kind = step["kind"]
        if kind == "none":
            r = "baseline"
        elif kind == "bar":
            r = osa(BAR, step["name"])
        elif kind == "menu":
            r = osa(MENU, *step["path"])
        elif kind == "dragslider":
            r = drag_control(step)
        elif kind == "sheet":
            r = osa(MENU, *step["path"]) if step.get("path") else "opened"
            if not r.startswith("ERROR"):
                r = osa(SHEET, step.get("radio", ""), step.get("button", "Create"))
        elif kind == "clickpop":
            clicks = step.get("clicks") or [step["at"]]
            r = click_popover(step["path"], clicks, step.get("keys", ()))
        elif kind == "popover":
            path = step["path"] + [""] * (3 - len(step["path"]))
            names = step.get("names") or [step["name"]]
            r = osa(POPOVER, *path, step.get("role", "AXCheckBox"), *names)
        elif kind in ("press", "increment", "decrement", "choose", "setvalue"):
            r = osa(SETTINGS, step["pane"], kind, step.get("role", "AXCheckBox"), step["name"],
                    str(step.get("nth", 1)), step.get("arg", ""))
        else:
            r = "unknown kind"
        label = step["label"]
        line = f"{n:02d} {label}: {r}"
        print(line, flush=True); log.write(line + "\n"); log.flush()
        if r.startswith("ERROR"):
            log.write("error - stopping\n"); log.flush()
            print("error - stopping", flush=True)
            break
        if r.startswith("NOTFOUND"):
            n += 1
            continue
        time.sleep(0.5)
        w = osa(SAVEAS, f"CLAUDE {PREFIX} {n:02d} {label} (Logic save)", OUT)
        log.write(f"   saved: {w}\n"); log.flush()
        if w.startswith("NO ") or not w.strip():
            log.write("save failed - stopping\n"); log.flush()
            print("save failed - stopping", flush=True)
            break
        n += 1
    log.write("loop done\n"); log.close()
    print("loop done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
