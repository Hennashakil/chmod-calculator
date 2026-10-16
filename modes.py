"""Parse and explain Linux permission modes, such as 750 or rwxr-x---.

Pure functions only: no file access, no shell, so user input can never
touch the server's file system.
"""

import re

OCTAL_RE = re.compile(r"^[0-7]{3,4}$")
SYMBOLIC_RE = re.compile(r"^[-dlbcps]?([r-][w-][xsS-])([r-][w-][xsS-])([r-][w-][xtT-])$")

WHO = ("owner", "group", "other")

# Plain words for beginners: who each set of letters is for, and what each letter means
LABEL = {"owner": "Owner", "group": "Group", "other": "Everyone else"}
WHO_PLAIN = {
    "owner": "the user who owns the file (usually whoever created it)",
    "group": "users in the file's group, like a team",
    "other": "every other user on the computer",
}
SWITCHES = (("r", 4, "read"), ("w", 2, "change"), ("x", 1, "run"))
SETUID, SETGID, STICKY = 4, 2, 1


class ModeError(ValueError):
    """Raised for input that is not a valid permission mode."""


def parse(text):
    """Return (special, [owner, group, other]) as integers 0-7."""
    text = (text or "").strip()
    if len(text) > 12:
        raise ModeError("Too long. Use 3 or 4 octal digits (750) or 9 letters (rwxr-x---).")
    if OCTAL_RE.match(text):
        digits = [int(c) for c in text.zfill(4)]
        return digits[0], digits[1:]
    m = SYMBOLIC_RE.match(text)
    if m:
        special, perms = 0, []
        for i, triplet in enumerate(m.groups()):
            value = (4 if triplet[0] == "r" else 0) | (2 if triplet[1] == "w" else 0)
            if triplet[2] in "xst":
                value |= 1
            if triplet[2] in "sStT":
                special |= (SETUID, SETGID, STICKY)[i]
            perms.append(value)
        return special, perms
    raise ModeError("Not a permission mode. Try 3 or 4 octal digits (750, 4755) "
                    "or 9 letters (rwxr-x---).")


def to_symbolic(special, perms):
    out = []
    for i, value in enumerate(perms):
        r = "r" if value & 4 else "-"
        w = "w" if value & 2 else "-"
        x = value & 1
        flag = (SETUID, SETGID, STICKY)[i]
        if special & flag:
            mark = ("s", "s", "t")[i]
            c = mark if x else mark.upper()
        else:
            c = "x" if x else "-"
        out.append(r + w + c)
    return "".join(out)


def _abilities(value):
    file_can, dir_can = [], []
    if value & 4:
        file_can.append("read it")
        dir_can.append("list what is inside")
    if value & 2:
        file_can.append("change it")
        dir_can.append("add, rename or delete entries (with x)")
    if value & 1:
        file_can.append("run it as a program")
        dir_can.append("pass through it")
    return file_can or ["nothing"], dir_can or ["nothing"]


def _switches(value):
    """Each letter as a switch: [{letter, on, value, meaning}], plus the sum, like 4 + 1 = 5."""
    switches = [{"letter": letter, "on": bool(value & v), "value": v, "meaning": meaning}
                for letter, v, meaning in SWITCHES]
    on = [str(sw["value"]) for sw in switches if sw["on"]]
    if not on:
        total = "0, every switch off"
    elif len(on) == 1:
        total = f"{on[0]}"
    else:
        total = f"{' + '.join(on)} = {value}"
    return switches, total


def _warnings(special, perms):
    owner, group, other = perms
    w = []
    if special == 0 and perms == [7, 7, 7]:
        w.append(("danger", "777 gives every user on the system full control. "
                  "Find the narrowest mode that still works instead."))
    elif other & 2:
        w.append(("danger", "Everyone on the system can change this. On a folder, "
                  "anyone can also delete other people's files inside it."))
    if special & SETUID:
        w.append(("danger", "setuid: the program runs with its owner's rights. If root "
                  "owns it, any bug in it can become a root exploit."))
    if special & SETGID:
        w.append(("warn", "setgid: on a program, it runs with the file's group rights; "
                  "on a folder, new files inherit the folder's group."))
    if special & STICKY:
        w.append(("info", "Sticky bit: in a shared folder like /tmp, people can only "
                  "delete their own files."))
    if (group & ~owner) or (other & ~owner):
        w.append(("warn", "The owner has fewer rights than group or other. Linux never "
                  "falls back for the owner, so the owner gets only the owner bits."))
    if not w:
        w.append(("ok", "No red flags."))
    return [{"level": lvl, "text": t} for lvl, t in w]


def explain(text):
    """Explain a mode. Raises ModeError for bad input."""
    special, perms = parse(text)
    octal = f"{special}{perms[0]}{perms[1]}{perms[2]}"
    short = octal[1:] if special == 0 else octal
    classes = []
    for who, value in zip(WHO, perms):
        file_can, dir_can = _abilities(value)
        switches, total = _switches(value)
        classes.append({
            "who": who,
            "label": LABEL[who],
            "who_plain": WHO_PLAIN[who],
            "switches": switches,
            "sum": total,
            "digit": value,
            "bits": to_symbolic(0, [value, 0, 0])[:3],
            "file": file_can,
            "folder": dir_can,
        })
    letters = {"owner": "u", "group": "g", "other": "o"}
    parts = []
    for i, c in enumerate(classes):
        perms_letters = c["bits"].replace("-", "")
        if special & (SETUID, SETGID, STICKY)[i]:
            perms_letters += ("s", "s", "t")[i]
        parts.append(f"{letters[c['who']]}={perms_letters}")
    return {
        "input": text.strip(),
        "octal": short,
        "symbolic": to_symbolic(special, perms),
        "chmod_octal": f"chmod {short} FILE",
        "chmod_symbolic": f"chmod {','.join(parts)} FILE",
        "classes": classes,
        "special": [name for flag, name in ((SETUID, "setuid"), (SETGID, "setgid"),
                                            (STICKY, "sticky")) if special & flag],
        "warnings": _warnings(special, perms),
    }
