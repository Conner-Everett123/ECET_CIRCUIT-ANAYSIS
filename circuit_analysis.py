# -*- coding: utf-8 -*-
"""
OHMS
"""

# -*- coding: utf-8 -*-
"""
Circuit Analysis Helper -- guided interactive menu for basic ECET concepts

    1) Ohm's Law         V = I x R
    2) Power             P = V x I = I^2 x R = V^2 / R
    3) Resistors         equivalent resistance, all series or all parallel
    4) KVL               loop voltages sum to 0   (check, or solve ONE unknown)
    5) KCL               node currents sum to 0   (check, or solve ONE unknown)
    6) Voltage Divider   series resistors share the source voltage
    7) Current Divider   parallel resistors split the total current
    8) Help              what each tool can and can't do

Every tool shows its WORK (formula -> numbers plugged in -> answer).
Numbers can use SI suffixes:  4.7k = 4700,  2m = 0.002,  10u = 0.00001

Every topic is its own class (init / grab_inputs / calculate) and the menu at
the bottom just loads them. Run this file directly to start:  python circuit_analysis.py
"""
import os
import sys
import textwrap

import numpy as np

# Set to True / False to force colors on / off. None = automatic.
USE_COLOR = None


# =============================================================================
# Look and feel -- colors, boxes, symbols, tables
# =============================================================================
def _color_enabled():
    if USE_COLOR is not None:
        return USE_COLOR
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _can_encode(text):
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        text.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


COLOR = _color_enabled()
if COLOR and os.name == "nt":
    os.system("")                       # lets Windows terminals show ANSI colors

UNI = _can_encode("Ω×→─│┌┐└┘✓✗•²Σµ")
OHM = "Ω" if UNI else "ohms"
TIMES = "×" if UNI else "x"
ARROW = "→" if UNI else "->"
SQ = "²" if UNI else "^2"
SIGMA = "Σ" if UNI else "sum"
MICRO = "µ" if UNI else "u"
CHECK = "✓" if UNI else "OK"
CROSS = "✗" if UNI else "X"
DOT = "•" if UNI else "*"
H, VBAR, TL, TR, BL, BR = ("─", "│", "┌", "┐", "└", "┘") if UNI else ("-", "|", "+", "+", "+", "+")
WIDTH = 68

CODES = {"bold": "1", "dim": "2", "red": "31", "green": "32", "yellow": "33",
         "blue": "34", "magenta": "35", "cyan": "36"}
PREFIXES = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, MICRO), (1e-9, "n")]
SUFFIXES = {"G": 1e9, "M": 1e6, "k": 1e3, "K": 1e3, "m": 1e-3, "u": 1e-6, "µ": 1e-6, "n": 1e-9, "p": 1e-12}


def c(text, *styles):
    """Wrap text in color/style codes (does nothing when colors are off)."""
    if not COLOR or not styles:
        return text
    return f"\033[{';'.join(CODES[s] for s in styles)}m{text}\033[0m"


def box(lines, title=None, color="cyan"):
    """Draw a box. Each line is 'text' or ('text', 'style1 style2'). Long lines wrap."""
    inner = WIDTH - 4
    if title:
        label = f" {title} "
        top = TL + H + label + H * (WIDTH - 3 - len(label)) + TR
    else:
        top = TL + H * (WIDTH - 2) + TR
    print(c(top, color))

    for line in lines:
        text, style = line if isinstance(line, tuple) else (line, "")
        stripped = text.lstrip()
        lead = len(text) - len(stripped)
        hang = lead + (2 if stripped[:2] in ("+ ", "- ", "* ") else 0)
        parts = textwrap.wrap(text, inner, subsequent_indent=" " * hang) or [""]
        for part in parts:
            print(c(VBAR, color) + " " + c(part.ljust(inner), *style.split()) + " " + c(VBAR, color))

    print(c(BL + H * (WIDTH - 2) + BR, color))


def table(headers, rows):
    """Print a simple aligned table (first column left, the rest right-aligned)."""
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]

    def fmt(row):
        cells = [str(row[0]).ljust(widths[0])]
        cells += [str(x).rjust(w) for x, w in zip(row[1:], widths[1:])]
        return "  ".join(cells)

    print("  " + c(fmt(headers), "bold", "cyan"))
    print("  " + c(H * (sum(widths) + 2 * (len(widths) - 1)), "dim"))
    for row in rows:
        print("  " + fmt(row))
    print()


def tool_title(title, formula=""):
    print()
    print(c(f" {title}", "bold", "magenta") + (c(f"    {formula}", "dim") if formula else ""))
    print(c(" " + H * (WIDTH - 2), "dim"))


def good(msg):
    print(c(f" {CHECK} {msg}", "green"))


def bad(msg):
    print(c(f" {CROSS} {msg}", "red"))


def note(msg):
    print(c(f" {DOT} {msg}", "yellow"))


def show_work(lines):
    box(lines, title="Work", color="blue")


def show_answer(lines, color="green"):
    box(lines, title="Answer", color=color)


def num(x):
    """Plain number for showing work: 12000.0 -> 12000, 0.5 -> 0.5"""
    return "0" if x == 0 else f"{x:.6g}"


def par(x):
    """Like num, but negatives get parentheses: -5 -> (-5)"""
    return f"({num(x)})" if x < 0 else num(x)


def eng(x, unit):
    """Engineering notation: 0.002, 'A' -> '2 mA'    4700, OHM -> '4.7 kΩ'"""
    if x == 0 or not np.isfinite(x):
        return f"{num(x)} {unit}"
    for scale, prefix in PREFIXES:
        if abs(x) >= scale:
            return f"{x / scale:.4g} {prefix}{unit}"
    return f"{x:.4g} {unit}"


def terms(values):
    return " + ".join(par(v) for v in values)


# =============================================================================
# Input helpers -- every prompt in the program goes through these
# =============================================================================
def ask(label):
    return input(c(" ? ", "cyan", "bold") + label + c("  > ", "cyan", "bold"))


def parse_number(raw):
    """float() that also understands SI suffixes: 4.7k, 2m, 10u, 1M ..."""
    raw = raw.strip()
    if raw and raw[-1] in SUFFIXES:
        value = float(raw[:-1]) * SUFFIXES[raw[-1]]
    else:
        value = float(raw)
    if not np.isfinite(value):
        raise ValueError
    return value


def ask_number(label, positive=False, nonzero=False):
    while True:
        try:
            value = parse_number(ask(label))
        except ValueError:
            bad("That isn't a number. Try something like 4.7, 1000, 4.7k or 2m.")
            continue
        if positive and value <= 0:
            bad("That value must be greater than 0.")
            continue
        if nonzero and value == 0:
            bad("That value can't be 0.")
            continue
        return value


def ask_yes_no(question, default=True):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        raw = ask(f"{question} {hint}").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        bad("Please answer y or n.")


def ask_choice(question, options):
    """Show a numbered list and return the chosen index (0-based)."""
    print()
    print(c(f" {question}", "bold"))
    for n, option in enumerate(options, start=1):
        print(f"   {c(str(n), 'cyan', 'bold')}  {option}")
    while True:
        raw = ask("Choose").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        bad(f"Enter a number from 1 to {len(options)}.")


def read_values(label):
    """Collect a list of numbers, one prompt each."""
    values = []
    while True:
        values.append(ask_number(label))
        if not ask_yes_no("Add another one?", default=False):
            break
    return np.array(values)


def read_resistors(label):
    """Collect resistor values, numbering them R1, R2, ..."""
    rt = []
    while True:
        rt.append(ask_number(f"{label} R{len(rt) + 1} ({OHM})", positive=True))
        if not ask_yes_no("Add another resistor?", default=False):
            break
    return np.array(rt)


# =============================================================================
# KVL -- Kirchhoff's Voltage Law
# =============================================================================
class KVL:
    def __init__(self, voltages=None):
        super().__init__()
        self.voltages = voltages

    def calculate_kvl(self, rt=None, It=None, vt=None):
        """Return the net loop sum (should be ~0 for a valid loop)."""
        if rt is not None and It is not None and len(rt) > 0:
            return float(0.0 - np.sum(np.multiply(rt, It)))

        if vt is not None and len(vt) > 0:
            return float(0.0 - np.sum(vt))

        return 0.0

    def solve_unknown(self, known_voltages):
        """Solve for ONE missing voltage: 0 = x + 12 + (-5) + (-3) -> x = -4.
        Rises are positive, drops are negative. A negative answer is a drop."""
        return 0.0 - float(np.sum(known_voltages))

    def grab_inputs(self):
        if not ask_yes_no("Do you already know the voltages?  (n = enter I and R instead)"):
            rt = []
            It = []
            while True:
                rt.append(ask_number(f"Resistor R{len(rt) + 1} ({OHM})", positive=True))
                It.append(ask_number("Current through it in A (negative if against the loop)"))
                if not ask_yes_no("Add another resistor?", default=False):
                    break
            return np.array(rt), np.array(It)

        return read_values("Voltage in V (rise +, drop -)")


# =============================================================================
# KCL -- Kirchhoff's Current Law
#   current ENTERING the node = positive, LEAVING the node = negative
# =============================================================================
class KCL:
    def __init__(self, currents=None):
        super().__init__()
        self.currents = currents

    def calculate_kcl(self, rt=None, vt=None, It=None):
        """Return the net current at the node (should be ~0 for a valid node)."""
        if rt is not None and vt is not None and len(rt) > 0:
            return float(np.sum(np.divide(vt, rt)))      # I = V / R per branch

        if It is not None and len(It) > 0:
            return float(np.sum(It))

        return 0.0

    def solve_unknown(self, known_currents):
        """Solve for ONE missing current: 0 = x + 1 + 6 + 10 + (-10) -> x = -7."""
        return 0.0 - float(np.sum(known_currents))

    def grab_inputs(self):
        if not ask_yes_no("Do you already know the currents?  (n = enter V and R per branch)"):
            rt = []
            vt = []
            while True:
                rt.append(ask_number(f"Branch resistor R{len(rt) + 1} ({OHM})", positive=True))
                vt.append(ask_number("Branch voltage in V (negative = current leaving the node)"))
                if not ask_yes_no("Add another branch?", default=False):
                    break
            return np.array(rt), np.array(vt)

        return read_values("Current in A (entering +, leaving -)")


# =============================================================================
# Ohms -- V = I * R  (pick what to find, enter the other two)
# =============================================================================
class Ohms:
    def __init__(self, voltage=None, current=None, resistance=None):
        super().__init__()
        self.voltage = voltage
        self.current = current
        self.resistance = resistance

    def calculate_ohms(self, v=None, i=None, r=None):
        """Return (label, value) for whichever of V, I, R is missing, else None."""
        if [v, i, r].count(None) != 1:
            return None

        if v is None:
            return "V", i * r          # V = I * R

        if i is None:
            if r <= 0:
                return None
            return "I", v / r          # I = V / R

        if r is None:
            if i == 0:
                return None
            return "R", v / i          # R = V / I

    def grab_inputs(self):
        target = ask_choice("What do you want to find?",
                            ["Voltage     (V)", "Current     (I)", "Resistance  (R)"])
        v = i = r = None
        if target != 0:
            v = ask_number("Voltage in V")
        if target != 1:
            i = ask_number("Current in A", nonzero=(target == 2))
        if target != 2:
            r = ask_number(f"Resistance in {OHM}", positive=True)
        return v, i, r


# =============================================================================
# Power -- P = V*I, I^2*R, or V^2/R  (pick what you know)
#   P = V*I is + when a part ABSORBS power, - when it SUPPLIES power
# =============================================================================
class Power:
    def __init__(self, voltage=None, current=None, resistance=None):
        super().__init__()
        self.voltage = voltage
        self.current = current
        self.resistance = resistance

    def calculate_power(self, v=None, i=None, r=None):
        """Return (\"P\", watts) using whichever two values were given, else None."""
        if [v, i, r].count(None) != 1:
            return None

        if r is None:
            return "P", v * i          # P = V * I

        if r <= 0:
            return None

        if v is None:
            return "P", i ** 2 * r     # P = I^2 * R

        if i is None:
            return "P", v ** 2 / r     # P = V^2 / R

    def grab_inputs(self):
        known = ask_choice("What do you know?",
                           ["Voltage and current      (V, I)",
                            "Current and resistance   (I, R)",
                            "Voltage and resistance   (V, R)"])
        v = i = r = None
        if known in (0, 2):
            v = ask_number("Voltage in V")
        if known in (0, 1):
            i = ask_number("Current in A")
        if known in (1, 2):
            r = ask_number(f"Resistance in {OHM}", positive=True)
        return v, i, r


# =============================================================================
# Resistors -- equivalent resistance of resistors ALL in series or ALL in parallel
#   series:    Req = R1 + R2 + ... + Rn
#   parallel:  1/Req = 1/R1 + 1/R2 + ... + 1/Rn
# =============================================================================
class Resistors:
    def __init__(self, resistors=None):
        super().__init__()
        self.resistors = resistors

    def calculate_resistors(self, rt=None, mode="series"):
        """Return the equivalent resistance in ohms, else None."""
        if rt is None or len(rt) == 0:
            return None

        rt = np.array(rt, dtype=float)
        if np.any(rt <= 0):
            return None

        if mode == "series":
            return float(np.sum(rt))              # Req = R1 + R2 + ...

        if mode == "parallel":
            return float(1 / np.sum(1 / rt))      # 1/Req = 1/R1 + 1/R2 + ...

        return None

    def grab_inputs(self):
        mode = ["series", "parallel"][ask_choice("How are the resistors connected?",
                                                 ["Series", "Parallel"])]
        return mode, read_resistors("Resistor")


# =============================================================================
# VoltageDivider -- series resistors: Vx = Vs * Rx / R_total
# =============================================================================
class VoltageDivider:
    def __init__(self, voltage=None, resistors=None):
        super().__init__()
        self.voltage = voltage
        self.resistors = resistors

    def calculate_divider(self, vs=None, rt=None):
        """Return an array of the voltage drop across each series resistor, else None."""
        if vs is None or rt is None or len(rt) == 0:
            return None

        rt = np.array(rt, dtype=float)
        if np.any(rt <= 0):
            return None

        return vs * rt / np.sum(rt)

    def grab_inputs(self):
        vs = ask_number("Source voltage in V")
        return vs, read_resistors("Series resistor")


# =============================================================================
# CurrentDivider -- parallel resistors: Ix = It * (1/Rx) / sum(1/R)
#   a SMALLER resistor takes MORE current
# =============================================================================
class CurrentDivider:
    def __init__(self, current=None, resistors=None):
        super().__init__()
        self.current = current
        self.resistors = resistors

    def calculate_divider(self, It=None, rt=None):
        """Return an array of the current through each parallel resistor, else None."""
        if It is None or rt is None or len(rt) == 0:
            return None

        rt = np.array(rt, dtype=float)
        if np.any(rt <= 0):
            return None

        g = 1 / rt                      # conductance of each branch
        return It * g / np.sum(g)

    def grab_inputs(self):
        It = ask_number("Total current entering the branches in A")
        return It, read_resistors("Parallel resistor")


# =============================================================================
# What each tool can and can't do -- shown before every topic
# =============================================================================
GENERAL_NOTE = [
    "All tools assume DC circuits with ideal resistors.",
    "SI suffixes work:  4.7k = 4700,  2m = 0.002,  10u = 0.00001",
    "Rule of thumb: you need ONE equation for EACH unknown.",
]

LIMITS = {
    "ohms": {
        "title": "Ohm's Law",
        "formula": f"V = I {TIMES} R",
        "can": ["Solve for ONE unknown (V, I or R) when you know the other two."],
        "cannot": [
            "Solve for two or more unknowns at once (one equation = one unknown).",
            "Handle a whole circuit -- it works on a single resistor or one equivalent resistance.",
        ],
    },
    "power": {
        "title": "Power",
        "formula": f"P = V{TIMES}I = I{SQ}{TIMES}R = V{SQ}/R",
        "can": ["Find the power of ONE component from any two of V, I, R."],
        "cannot": [
            "Total the power of a whole circuit (calculate each part, then add them yourself).",
            "Solve backwards for V, I or R from a known power.",
        ],
    },
    "res": {
        "title": "Resistors (equivalent resistance)",
        "formula": f"series: {SIGMA}R    parallel: 1/Req = {SIGMA}(1/R)",
        "can": ["Combine resistors that are ALL in series OR ALL in parallel into one equivalent resistor."],
        "cannot": [
            "Reduce a mixed series-parallel network in one go -- do it in steps: combine each "
            "group, then use the result as one resistor in the next pass.",
            "Handle Y-Delta networks or anything with sources inside the network.",
        ],
    },
    "kvl": {
        "title": "KVL (Kirchhoff's Voltage Law)",
        "formula": f"{SIGMA}V around a loop = 0",
        "can": [
            "Check that ONE closed loop balances (all voltages known).",
            "Solve for ONE unknown voltage in ONE loop.",
        ],
        "cannot": [
            "Solve for two or more unknowns at once.",
            "Handle several loops at the same time (that needs mesh analysis).",
        ],
    },
    "kcl": {
        "title": "KCL (Kirchhoff's Current Law)",
        "formula": f"{SIGMA}I at a node = 0   (in +, out -)",
        "can": [
            "Check that ONE node balances (all currents known).",
            "Solve for ONE unknown current at ONE node.",
        ],
        "cannot": [
            "Solve for two or more unknowns at once.",
            "Handle several nodes at the same time (that needs nodal analysis).",
        ],
    },
    "vdiv": {
        "title": "Voltage Divider",
        "formula": f"Vx = Vs {TIMES} Rx / Rtotal",
        "can": ["Find the voltage across EVERY resistor in a series string with one source."],
        "cannot": [
            "Handle parallel branches -- combine them into one equivalent resistor first (option 3).",
            "Account for a load connected across one of the resistors (loading effect).",
        ],
    },
    "idiv": {
        "title": "Current Divider",
        "formula": f"Ix = It {TIMES} (1/Rx) / {SIGMA}(1/R)",
        "can": ["Find the current through EVERY resistor in a parallel set with one total current."],
        "cannot": [
            "Handle series resistors inside a branch -- combine them into one resistor first (option 3).",
            "Work with a source voltage -- it needs the TOTAL current entering the branches.",
        ],
    },
}


def show_limits(key):
    info = LIMITS[key]
    lines = [("CAN DO", "bold green")]
    lines += [(f"  + {t}", "green") for t in info["can"]]
    lines += [("", ""), ("CAN'T DO", "bold red")]
    lines += [(f"  - {t}", "red") for t in info["cannot"]]
    lines += [("", ""), ("Remember: you need ONE equation for EACH unknown.", "yellow")]
    box(lines, title=info["title"], color="blue")


# =============================================================================
# Tool screens -- one function per topic: ask -> calculate -> show work -> answer
# =============================================================================
def run_help():
    tool_title("Help", "what each tool can and can't do")
    box([(t, "") for t in GENERAL_NOTE], title="Before you start", color="yellow")
    for key in LIMITS:
        print()
        show_limits(key)


def run_ohms():
    circuit = Ohms()
    v, i, r = circuit.grab_inputs()
    result = circuit.calculate_ohms(v=v, i=i, r=r)

    if result is None:
        bad("Could not solve with those values.")
        return

    label, value = result
    units = {"V": "V", "I": "A", "R": OHM}
    if label == "V":
        work = [f"V = I {TIMES} R", f"V = {par(i)} {TIMES} {par(r)}"]
    elif label == "I":
        work = ["I = V / R", f"I = {par(v)} / {par(r)}"]
    else:
        work = ["R = V / I", f"R = {par(v)} / {par(i)}"]

    print()
    show_work(work)
    show_answer([(f"{label} = {eng(value, units[label])}", "bold green")])
    if label == "R" and value <= 0:
        note("Resistance should be positive -- check the signs of V and I.")


def run_power():
    circuit = Power()
    v, i, r = circuit.grab_inputs()
    result = circuit.calculate_power(v=v, i=i, r=r)

    if result is None:
        bad("Could not solve with those values.")
        return

    _, watts = result
    if r is None:
        work = [f"P = V {TIMES} I", f"P = {par(v)} {TIMES} {par(i)}"]
    elif v is None:
        work = [f"P = I{SQ} {TIMES} R", f"P = {par(i)}{SQ} {TIMES} {num(r)}"]
    else:
        work = [f"P = V{SQ} / R", f"P = {par(v)}{SQ} / {num(r)}"]

    print()
    show_work(work)
    show_answer([(f"P = {eng(watts, 'W')}", "bold green")])
    if r is None and watts > 0:
        note("Positive power: the part is ABSORBING power.")
    elif r is None and watts < 0:
        note("Negative power: the part is SUPPLYING power.")


def run_resistors():
    circuit = Resistors()
    mode, rt = circuit.grab_inputs()
    req = circuit.calculate_resistors(rt=rt, mode=mode)

    if req is None:
        bad("Could not solve with those values.")
        return

    if mode == "series":
        work = ["Req = R1 + R2 + ... + Rn",
                f"Req = {' + '.join(num(r) for r in rt)}"]
    else:
        total_g = float(np.sum(1 / rt))
        work = ["1/Req = 1/R1 + 1/R2 + ... + 1/Rn",
                f"1/Req = {' + '.join('1/' + num(r) for r in rt)} = {num(total_g)}",
                f"Req = 1 / {num(total_g)}"]
        if len(rt) == 2:
            work.append(f"Shortcut for two: Req = (R1 {TIMES} R2) / (R1 + R2)")

    print()
    show_work(work)
    show_answer([(f"Req ({mode}) = {eng(req, OHM)}", "bold green")])
    if len(rt) > 1:
        if mode == "series":
            note(f"Check: series Req is bigger than the largest resistor ({eng(np.max(rt), OHM)}).")
        else:
            note(f"Check: parallel Req is smaller than the smallest resistor ({eng(np.min(rt), OHM)}).")


def run_kvl():
    circuit = KVL()
    mode = ask_choice("What do you want to do?",
                      ["Check that a loop balances (every voltage known)",
                       "Solve for ONE unknown voltage"])

    if mode == 1:
        known = read_values("KNOWN voltage in V (rise +, drop -)")
        x = circuit.solve_unknown(known)
        print()
        show_work([f"{SIGMA}V = 0", f"0 = x + {terms(known)}", f"x = -({terms(known)})"])
        kind = "a voltage RISE" if x >= 0 else "a voltage DROP"
        show_answer([(f"Unknown voltage x = {eng(x, 'V')}", "bold green"), (f"That is {kind}.", "")])
        return

    user_data = circuit.grab_inputs()
    if isinstance(user_data, tuple):
        rt, It = user_data
        net = circuit.calculate_kvl(rt=rt, It=It)
        parts = [f"({num(i)} {TIMES} {num(r)})" for r, i in zip(rt, It)]
        work = [f"{SIGMA}(I {TIMES} R) = {' + '.join(parts)}", f"{SIGMA}(I {TIMES} R) = {num(-net)} V"]
    else:
        net = circuit.calculate_kvl(vt=user_data)
        work = [f"{SIGMA}V = {terms(user_data)}", f"{SIGMA}V = {num(-net)} V"]

    print()
    show_work(work + ["KVL says this must equal 0."])
    if np.isclose(net, 0.0):
        show_answer([(f"{CHECK} KVL satisfied -- the loop balances.", "bold green")])
    else:
        show_answer([(f"{CROSS} KVL NOT satisfied -- {eng(abs(net), 'V')} left over.", "bold red")], color="red")


def run_kcl():
    circuit = KCL()
    mode = ask_choice("What do you want to do?",
                      ["Check that a node balances (every current known)",
                       "Solve for ONE unknown current"])

    if mode == 1:
        known = read_values("KNOWN current in A (entering +, leaving -)")
        x = circuit.solve_unknown(known)
        print()
        show_work([f"{SIGMA}I = 0", f"0 = x + {terms(known)}", f"x = -({terms(known)})"])
        direction = "ENTERING the node" if x >= 0 else "LEAVING the node"
        show_answer([(f"Unknown current x = {eng(x, 'A')}", "bold green"), (f"It is {direction}.", "")])
        return

    user_data = circuit.grab_inputs()
    if isinstance(user_data, tuple):
        rt, vt = user_data
        net = circuit.calculate_kcl(rt=rt, vt=vt)
        branches = np.divide(vt, rt)
        work = [f"I{n} = V{n} / R{n} = {par(v)} / {num(r)} = {num(i)} A"
                for n, (r, v, i) in enumerate(zip(rt, vt, branches), start=1)]
        work.append(f"{SIGMA}I = {terms(branches)} = {num(net)} A")
    else:
        net = circuit.calculate_kcl(It=user_data)
        work = [f"{SIGMA}I = {terms(user_data)} = {num(net)} A"]

    print()
    show_work(work + ["KCL says this must equal 0."])
    if np.isclose(net, 0.0):
        show_answer([(f"{CHECK} KCL satisfied -- currents in = currents out.", "bold green")])
    else:
        show_answer([(f"{CROSS} KCL NOT satisfied -- {eng(abs(net), 'A')} unaccounted for.", "bold red")], color="red")


def run_voltage_divider():
    circuit = VoltageDivider()
    vs, rt = circuit.grab_inputs()
    drops = circuit.calculate_divider(vs=vs, rt=rt)

    if drops is None:
        bad("Could not solve with those values.")
        return

    total_r = float(np.sum(rt))
    print()
    show_work([f"Vx = Vs {TIMES} Rx / Rtotal",
               f"Rtotal = {' + '.join(num(r) for r in rt)} = {eng(total_r, OHM)}",
               f"Example: V1 = {num(vs)} {TIMES} {num(rt[0])} / {num(total_r)} = {num(drops[0])} V"])

    rows = [(f"R{n}", eng(r, OHM), eng(v, "V"), f"{100 * r / total_r:.1f}%")
            for n, (r, v) in enumerate(zip(rt, drops), start=1)]
    print()
    table(["Resistor", "Value", "Voltage", "Share"], rows)

    total = float(np.sum(drops))
    show_answer([(f"{CHECK} Drops add up to {eng(total, 'V')} = the source (KVL).", "bold green")])
    note("The biggest resistor takes the biggest share of the voltage.")


def run_current_divider():
    circuit = CurrentDivider()
    It, rt = circuit.grab_inputs()
    branches = circuit.calculate_divider(It=It, rt=rt)

    if branches is None:
        bad("Could not solve with those values.")
        return

    g = 1 / rt
    total_g = float(np.sum(g))
    print()
    show_work([f"Ix = It {TIMES} (1/Rx) / {SIGMA}(1/R)",
               f"{SIGMA}(1/R) = {' + '.join('1/' + num(r) for r in rt)} = {eng(total_g, 'S')}",
               f"Example: I1 = {num(It)} {TIMES} (1/{num(rt[0])}) / {num(total_g)} = {num(branches[0])} A"])

    rows = [(f"R{n}", eng(r, OHM), eng(i, "A"), f"{100 * gx / total_g:.1f}%")
            for n, (r, i, gx) in enumerate(zip(rt, branches, g), start=1)]
    print()
    table(["Resistor", "Value", "Current", "Share"], rows)

    total = float(np.sum(branches))
    show_answer([(f"{CHECK} Branches add up to {eng(total, 'A')} = the total current (KCL).", "bold green")])
    note("The SMALLEST resistor takes the MOST current.")


# =============================================================================
# Interactive menu
# =============================================================================
ACTIONS = {
    "1": ("ohms", run_ohms),
    "2": ("power", run_power),
    "3": ("res", run_resistors),
    "4": ("kvl", run_kvl),
    "5": ("kcl", run_kcl),
    "6": ("vdiv", run_voltage_divider),
    "7": ("idiv", run_current_divider),
}


def print_menu():
    def item(num_, key):
        return f"  {num_}   {LIMITS[key]['title'].split(' (')[0]}"

    lines = [
        ("FUNDAMENTALS", "dim"),
        item(1, "ohms"), item(2, "power"), item(3, "res"),
        ("", ""),
        ("KIRCHHOFF'S LAWS", "dim"),
        item(4, "kvl"), item(5, "kcl"),
        ("", ""),
        ("DIVIDERS", "dim"),
        item(6, "vdiv"), item(7, "idiv"),
        ("", ""),
        "  8   Help -- what each tool can do",
        "  0   Quit",
    ]
    print()
    box(lines, title="MENU", color="cyan")


def main():
    try:
        print()
        box([("ECET Circuit Analysis Helper".center(WIDTH - 4), "bold"),
             ("guided practice for basic circuit concepts".center(WIDTH - 4), "dim")], color="magenta")
        print()
        box([(t, "") for t in GENERAL_NOTE], title="Before you start", color="yellow")

        while True:
            print_menu()
            choice = ask("Pick a topic (8 = help, 0 = quit)").strip()

            if choice == "0":
                print(c("\n Good luck with the circuits!\n", "bold", "magenta"))
                break

            if choice == "8":
                run_help()
                continue

            if choice not in ACTIONS:
                bad("Pick a number from the menu.")
                continue

            key, action = ACTIONS[choice]
            info = LIMITS[key]
            tool_title(info["title"].split(" (")[0], info["formula"])
            show_limits(key)

            while True:
                action()
                print()
                if not ask_yes_no("Run this tool again?", default=False):
                    break
                tool_title(info["title"].split(" (")[0], info["formula"])
    except (KeyboardInterrupt, EOFError):
        print(c("\n\n Good luck with the circuits!\n", "bold", "magenta"))


if __name__ == "__main__":
    main()
