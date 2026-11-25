# news-image-20261125 — main.py (V2)
#
# A one-page broadsheet that sums up the world's news of Wednesday
# 25 November 2026 in a single image. Python 3.13, standard library only,
# no network. The program draws the page itself (its own tiny rasteriser,
# its own 7x9 type, its own PNG writer) and writes /output/entry.png.
# It runs twice and writes identical bytes: every drawing decision is
# integer or fixed-seed arithmetic, nothing reads a clock or a RNG.
#
# Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for /output:
#   mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
#
# V3 changes over V2: verified UCL Wednesday finals added as a wire wrap
# (pool #63, replacing Tuesday's Arsenal-Dortmund brief); a world map
# panel takes the 4th feature-row slot (#36 demoted to the wire, its
# story stays on the page); #8's headline shortened to two lines;
# chart bars moved right so no bar touches its label; lead scene
# reworked (atmospheric rim instead of stripe glow, streak clouds,
# tapered smoke plume, visible launch pad, captioned station, short
# captions clear of the Earth arc); lead headline as a 2-line wrap at
# 2.6 with a taller scene; rail chip "JEDDAH THREATENED" finally drawn;
# wire floors raised and longest second lines trimmed; footer is now a
# pure source line (adds KPLER, CONF. BOARD). Font probes showed no
# typeface change helps OCR (slashed zero reads as B — rejected), so
# the 7x9 type stays as V2.
#
# The page carries exactly 37 stories from that day's reporting
# (Reuters, AP, AFP, Xinhua, WHO, UEFA, BEA, EPA and official releases):
#   1 lead, 1 markets chart panel, 1 feature in the rail,
#   3 features + 1 world map panel in a row, and 31 one-line wire briefs.

import math
import os
import struct
import zlib

# ---------------------------------------------------------------- type ----
# A 7x9 pixel typeface, drawn as data: nine rows of seven bits per glyph.
# Only the characters the page prints are defined; text is upper-case.
# Glyphs were drawn for distinctness: M has a full centre valley, C is
# open, 0 carries a slash, 1 has a foot, 5 and S differ in the top bar.

FONT = {
    "A": ("0011100", "0100010", "0100010", "0100010", "0111110", "0100010", "0100010", "0100010", "0100010"),
    "B": ("0111100", "0100010", "0100010", "0111100", "0100010", "0100010", "0100010", "0100010", "0111100"),
    "C": ("0011110", "0100001", "0100000", "0100000", "0100000", "0100000", "0100000", "0100001", "0011110"),
    "D": ("0111000", "0100100", "0100010", "0100010", "0100010", "0100010", "0100010", "0100100", "0111000"),
    "E": ("0111110", "0100000", "0100000", "0111100", "0100000", "0100000", "0100000", "0100000", "0111110"),
    "F": ("0111110", "0100000", "0100000", "0111100", "0100000", "0100000", "0100000", "0100000", "0100000"),
    "G": ("0011110", "0100001", "0100000", "0100000", "0100111", "0100001", "0100001", "0100001", "0011111"),
    "H": ("0100010", "0100010", "0100010", "0111110", "0100010", "0100010", "0100010", "0100010", "0100010"),
    "I": ("0111100", "0001000", "0001000", "0001000", "0001000", "0001000", "0001000", "0001000", "0111100"),
    "J": ("0000111", "0000010", "0000010", "0000010", "0000010", "0000010", "0100010", "0100010", "0011100"),
    "K": ("0100010", "0100100", "0101000", "0110000", "0101000", "0100100", "0100010", "0100010", "0100010"),
    "L": ("0100000", "0100000", "0100000", "0100000", "0100000", "0100000", "0100000", "0100000", "0111110"),
    "M": ("0100010", "0110110", "0111110", "0101010", "0101010", "0100010", "0100010", "0100010", "0100010"),
    "N": ("0100010", "0110010", "0111010", "0101110", "0100110", "0100010", "0100010", "0100010", "0100010"),
    "O": ("0011100", "0100010", "0100010", "0100010", "0100010", "0100010", "0100010", "0100010", "0011100"),
    "P": ("0111100", "0100010", "0100010", "0111100", "0100000", "0100000", "0100000", "0100000", "0100000"),
    "Q": ("0011100", "0100010", "0100010", "0100010", "0100010", "0101010", "0100110", "0001010", "0000110"),
    "R": ("0111100", "0100010", "0100010", "0111100", "0101000", "0100100", "0100010", "0100010", "0100010"),
    "S": ("0011110", "0100001", "0100000", "0011100", "0000010", "0000001", "0000001", "0100001", "0011110"),
    "T": ("0111110", "0001000", "0001000", "0001000", "0001000", "0001000", "0001000", "0001000", "0001000"),
    "U": ("0100010", "0100010", "0100010", "0100010", "0100010", "0100010", "0100010", "0100010", "0011100"),
    "V": ("0100010", "0100010", "0100010", "0100010", "0100010", "0100010", "0010100", "0010100", "0001000"),
    "W": ("0100010", "0100010", "0100010", "0100010", "0101010", "0101010", "0101010", "0110110", "0100010"),
    "X": ("0100010", "0100010", "0010100", "0001000", "0001000", "0001000", "0010100", "0100010", "0100010"),
    "Y": ("0100010", "0100010", "0010100", "0001000", "0001000", "0001000", "0001000", "0001000", "0001000"),
    "Z": ("0111110", "0000010", "0000100", "0001000", "0010000", "0100000", "0100000", "0100000", "0111110"),
    "0": ("0111100", "0100010", "0100010", "0100010", "0100010", "0100010", "0100010", "0100010", "0111100"),
    "1": ("0001000", "0011000", "0001000", "0001000", "0001000", "0001000", "0001000", "0001000", "0011100"),
    "2": ("0011100", "0100010", "0000010", "0000110", "0001000", "0010000", "0100000", "0100000", "0111110"),
    "3": ("0111100", "0000010", "0000010", "0011100", "0000010", "0000010", "0000010", "0000010", "0111100"),
    "4": ("0000100", "0001100", "0010100", "0100100", "0100010", "0111110", "0000010", "0000010", "0000010"),
    "5": ("0111110", "0100000", "0111100", "0000010", "0000010", "0000010", "0000010", "0100010", "0011100"),
    "6": ("0011100", "0100000", "0100000", "0111100", "0100010", "0100010", "0100010", "0100010", "0011100"),
    "7": ("0111110", "0000010", "0000100", "0001000", "0001000", "0010000", "0010000", "0010000", "0010000"),
    "8": ("0011100", "0100010", "0100010", "0011100", "0100010", "0100010", "0100010", "0100010", "0011100"),
    "9": ("0011100", "0100010", "0100010", "0100010", "0100010", "0011110", "0000010", "0000010", "0011100"),
    " ": ("0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000"),
    ".": ("0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0011000", "0011000"),
    ",": ("0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0011000", "0010000", "0100000"),
    "'": ("0001000", "0001000", "0010000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000"),
    "-": ("0000000", "0000000", "0000000", "0000000", "0111100", "0000000", "0000000", "0000000", "0000000"),
    ":": ("0000000", "0011000", "0011000", "0000000", "0011000", "0011000", "0000000", "0000000", "0000000"),
    ";": ("0000000", "0011000", "0011000", "0000000", "0011000", "0011000", "0010000", "0100000", "0000000"),
    "!": ("0001000", "0001000", "0001000", "0001000", "0001000", "0001000", "0000000", "0011000", "0011000"),
    "?": ("0011100", "0100010", "0000010", "0001100", "0001000", "0000000", "0001000", "0001000", "0000000"),
    "%": ("0110000", "0110000", "0000100", "0001000", "0010000", "0100000", "0000110", "0000110", "0000000"),
    "$": ("0001000", "0011110", "0100100", "0100100", "0011100", "0001010", "0101010", "0111100", "0001000"),
    "+": ("0000000", "0000000", "0001000", "0001000", "0011100", "0001000", "0001000", "0000000", "0000000"),
    "/": ("0000010", "0000010", "0000100", "0000100", "0001000", "0010000", "0010000", "0100000", "0100000"),
    "(": ("0000100", "0001000", "0010000", "0010000", "0010000", "0010000", "0010000", "0001000", "0000100"),
    ")": ("0010000", "0001000", "0000100", "0000100", "0000100", "0000100", "0000100", "0001000", "0010000"),
    "&": ("0011100", "0100010", "0100100", "0011000", "0101010", "0100100", "0100010", "0100010", "0011010"),
    '"': ("0101010", "0101010", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000", "0000000"),
    "*": ("0000000", "0001000", "0101010", "0011100", "0101010", "0001000", "0000000", "0000000", "0000000"),
}

FONT_W, FONT_H, ADV = 7, 9, 8

def clean(text):
    """Fold the few typographic characters the page uses into the type."""
    return (text.replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u2013", "-").replace("\u2014", "-")
                .replace("\u2212", "-").replace("\u00b7", "-")
                .upper())

# ------------------------------------------------------------- canvas -----

W, H, SS = 1024, 1024, 2            # page size and supersampling factor
CW, CH = W * SS, H * SS             # canvas size in device pixels

class Page:
    def __init__(self, bg):
        self.px = [bytearray(bg * CW) for _ in range(CH)]

    def _row_fill(self, y, x0, x1, rgb):
        row = self.px[y]
        row[x0 * 3:x1 * 3] = rgb * (x1 - x0)

    def rect(self, x, y, w, h, rgb):
        """Filled rectangle in page coordinates (floats allowed)."""
        x0, y0 = int(round(x * SS)), int(round(y * SS))
        x1, y1 = int(round((x + w) * SS)), int(round((y + h) * SS))
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(CW, x1), min(CH, y1)
        if x1 <= x0 or y1 <= y0:
            return
        for yy in range(y0, y1):
            self._row_fill(yy, x0, x1, rgb)

    def frame(self, x, y, w, h, rgb, t=2):
        self.rect(x, y, w, t, rgb)
        self.rect(x, y + h - t, w, t, rgb)
        self.rect(x, y, t, h, rgb)
        self.rect(x + w - t, y, t, h, rgb)

    def line(self, x0, y0, x1, y1, rgb, t=1.5):
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * SS * 2) + 1
        r = t / 2.0
        for i in range(steps + 1):
            f = i / steps
            self.rect(x0 + (x1 - x0) * f - r, y0 + (y1 - y0) * f - r,
                      t, t, rgb)

    def disc(self, cx, cy, rad, rgb, clip=None):
        """Filled disc in page coordinates, optionally clipped to a box."""
        x0, x1 = int((cx - rad) * SS), int((cx + rad) * SS) + 1
        y0, y1 = int((cy - rad) * SS), int((cy + rad) * SS) + 1
        if clip is not None:
            x0 = max(x0, int(clip[0] * SS))
            y0 = max(y0, int(clip[1] * SS))
            x1 = min(x1, int((clip[0] + clip[2]) * SS))
            y1 = min(y1, int((clip[1] + clip[3]) * SS))
        rr = (rad * SS) ** 2
        ccx, ccy = cx * SS, cy * SS
        for yy in range(max(0, y0), min(CH, y1)):
            for xx in range(max(0, x0), min(CW, x1)):
                if (xx - ccx) ** 2 + (yy - ccy) ** 2 <= rr:
                    row = self.px[yy]
                    row[xx * 3:xx * 3 + 3] = rgb

    def poly(self, pts, rgb):
        """Scanline-filled polygon in page coordinates."""
        ys = [p[1] for p in pts]
        y0, y1 = int(min(ys) * SS), int(max(ys) * SS) + 1
        n = len(pts)
        for yy in range(max(0, y0), min(CH, y1)):
            cy = (yy + 0.5) / SS
            xs = []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if (ay <= cy < by) or (by <= cy < ay):
                    xs.append(ax + (cy - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                xa, xb = int(xs[i] * SS), int(xs[i + 1] * SS) + 1
                xa, xb = max(0, xa), min(CW, xb)
                if xb > xa:
                    self._row_fill(yy, xa, xb, rgb)

    # -- text -------------------------------------------------------------
    def text_w(self, text, s):
        return len(clean(text)) * ADV * s - s

    def text(self, x, y, text, s, rgb, bold=False, align="left"):
        text = clean(text)
        w = self.text_w(text, s)
        if align == "center":
            x -= w / 2.0
        elif align == "right":
            x -= w
        thick = 0.45 * s if bold else 0.0
        for ch in text:
            glyph = FONT.get(ch, FONT[" "])
            for r in range(FONT_H):
                rowbits = glyph[r]
                for c in range(FONT_W):
                    if rowbits[c] == "1":
                        self.rect(x + c * s, y + r * s, s + thick, s, rgb)
            x += ADV * s
        return w

    def wrap(self, text, s, width):
        words = clean(text).split()
        lines, cur = [], ""
        for wd in words:
            trial = wd if not cur else cur + " " + wd
            if self.text_w(trial, s) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, text, s, rgb, width, step, bold=False):
        for ln in self.wrap(text, s, width):
            self.text(x, y, ln, s, rgb, bold=bold)
            y += step
        return y

    def fit_scale(self, text, s, width, floor=0.9):
        """Largest scale at or below s (step 0.05) that fits the width."""
        while s > floor and self.text_w(text, s) > width:
            s -= 0.05
        return s

    def finish(self):
        """Downsample the supersampled canvas to the page size."""
        out = bytearray(W * H * 3)
        for y in range(H):
            top = list(self.px[2 * y])
            bot = list(self.px[2 * y + 1])
            base = y * W * 3
            for x in range(W):
                i = x * 6
                o = base + x * 3
                out[o] = (top[i] + top[i + 3] + bot[i] + bot[i + 3]) // 4
                out[o + 1] = (top[i + 1] + top[i + 4] +
                              bot[i + 1] + bot[i + 4]) // 4
                out[o + 2] = (top[i + 2] + top[i + 5] +
                              bot[i + 2] + bot[i + 5]) // 4
        return bytes(out)

# -------------------------------------------------------------- palette ---

PAPER = bytes((247, 243, 231))
CARD = bytes((253, 251, 244))
INK = bytes((19, 21, 27))
MUTED = bytes((82, 86, 97))
NIGHT = bytes((13, 20, 38))
STAR = bytes((240, 238, 220))
FLAME = bytes((232, 119, 34))
EARTH = bytes((38, 84, 124))
RIM = bytes((110, 168, 214))
GLOW1 = bytes((52, 66, 98))
GLOW2 = bytes((30, 44, 72))
SMOKE = bytes((150, 158, 175))
PAD = bytes((8, 12, 22))
CLOUD = bytes((96, 148, 196))

BEAT = {
    "WAR": bytes((163, 30, 30)),
    "POLITICS": bytes((23, 74, 158)),
    "BUSINESS": bytes((14, 106, 66)),
    "WORLD": bytes((8, 106, 118)),
    "SCIENCE": bytes((128, 76, 0)),
    "SPORT": bytes((106, 32, 138)),
}

# -------------------------------------------------------------- stories ---
# Every story: (pool number, beat, short dateline, headline, body, chip).
# Figures are exactly as the day's reporting carried them (see the
# research pool); evolving counts use the AT LEAST floor form.

LEAD = (47, "SCIENCE", "JIUQUAN, CHINA",
        "SHENZHOU-24 LIFTS OFF WITH FIRST PAKISTANI IN ORBIT",
        "Shenzhou-24 launched from Jiuquan at 08:18 Wednesday carrying "
        "Tang Hongbo, Wu Yi and Muhammad Zeeshan Ali - the first "
        "Pakistani in orbit and Tiangong's first foreign visitor.",
        "FIRST PAKISTANI IN ORBIT")

CHART = (28, "BUSINESS", "TOKYO",
         "ASIA STOCKS TUMBLE ON TARIFF THREATS",
         "Fresh US tariff threats hit Asia early Wednesday.",
         "KOREA -5.3%")
CHART_BARS = (("SOUTH KOREA", -5.3), ("TAIWAN", -5.1),
              ("NIKKEI*", -2.9), ("MSCI APAC", -2.3))

RAIL = (1, "WAR", "JEDDAH",
        "HOUTHIS THREATEN JEDDAH, ALL SAUDI PORTS",
        "Yemen's Houthis said Jeddah and every Saudi Red Sea port will "
        "be targeted if Hodeidah is hit; the coalition struck back.",
        "JEDDAH THREATENED")

FEATURES = [
    (8, "WAR", "MOSCOW",
     "RUSSIA'S WAR DEAD PASS 490,000",
     "At least 490,000 confirmed registered deaths, breached-data "
     "count; estimates 700,000 (Meduza/Mediazona).",
     "AT LEAST 490,000 DEAD"),
    (15, "POLITICS", "CANBERRA",
     "AUSTRALIA, SOLOMONS SIGN SECURITY TREATY",
     "Treaty signed in Canberra makes Australia the Solomons' primary "
     "security partner; no foreign base allowed.",
     "PARTNER OF CHOICE"),
    (62, "BUSINESS", "WASHINGTON",
     "CORE INFLATION RISES TO 3.3%",
     "Core PCE rose 0.3% to 3.3% year on year, above the 3.2% forecast; "
     "headline 3.8%; a December rate rise is expected.",
     "CORE PCE 3.3%"),
]

# The 4th feature-row slot is the world map panel (drawn by
# draw_map_panel), not a story. #36 was demoted to the wire so the map
# has a slot; its story stays on the page.

# Wire briefs: (pool, beat, headline, one terse line). 31 of them,
# reordered round-robin by beat so no beat is buried at the bottom.
# #63 is the verified Wednesday-night UCL wrap (all nine finals
# cross-checked: Times / OneFootball / Sportradar); it replaces #53,
# Tuesday's Arsenal-Dortmund draw. #36 joins the wire from the
# feature row to make room for the world map panel.
WIRE = [
    (2, "WAR", "DRONE HITS RIYADH'S TALLEST TOWER AGAIN",
     "RIYADH - PIF TOWER HIT; AT LEAST 11 HURT"),
    (12, "POLITICS", "TRUMP READIES NEW TARIFF WAVE",
     "WASHINGTON - CAPACITY PROBE, 16 PARTNERS"),
    (29, "BUSINESS", "NVIDIA SLIDES AS HYPE FADES",
     "NEW YORK - NVIDIA -5.9%; DOW ROSE 0.9%"),
    (37, "WORLD", "ARMY DETONATES 9,500 POUNDS OF LEAD AZIDE",
     "IOWA - BLAST DONE; EPA: NO LEAD DETECTED"),
    (48, "SCIENCE", "OLDEST QUASAR 13.1 BILLION YEARS BACK",
     "SPACE - EUCLID FIND; BLACK HOLE 360M SUNS"),
    (52, "SPORT", "MADRID ROUT PSV 5-1",
     "MADRID - MBAPPE TWICE, FIVE FROM FIVE"),
    (3, "WAR", "HOUTHIS CLOSE TO 60 KM OF ADEN",
     "ADEN - PORT 'WILL NOT FALL', ARMY SAYS"),
    (13, "POLITICS", "HUAWEI CONVICTED IN NEW YORK COURT",
     "NEW YORK - GUILTY ON 10 OF 12; WILL APPEAL"),
    (30, "BUSINESS", "CONSUMER CONFIDENCE JUMPS TO 103.3",
     "NEW YORK - UP 11.4 PTS, BEST SINCE JAN 2025"),
    (39, "WORLD", "WHO EVACUATES HOSPITAL AMID FIGHTING",
     "ITURI - EBOLA TOLL STANDS AT 5,775 DEATHS"),
    (49, "SCIENCE", "TITANIUM OXIDE FOUND AROUND YOUNG STAR",
     "SPACE - ALMA READS ORION SOURCE I'S AIR"),
    (56, "SPORT", "ENGLAND LEVEL T20 SERIES IN AUSTRALIA",
     "GOLD COAST - DONALD 85 OFF 32; SERIES 1-1"),
    (4, "WAR", "RUSSIAN STRIKE ON ODESA KILLS TWO",
     "ODESA - TWO DEAD, THREE HURT; KYIV HIT TOO"),
    (14, "POLITICS", "SHANGHAI CHIEF UNDER GRAFT PROBE",
     "SHANGHAI - CHEN JINING, 4TH PROBE SINCE 2025"),
    (31, "BUSINESS", "BITCOIN SLIPS BELOW $60,000",
     "NEW YORK - $59,257.71; $4.71BN ETF OUTFLOW"),
    (41, "WORLD", "25 HELD HOSTAGE IN SUPERMARKET",
     "CARTAGENA - HIJACK FAILS; FIVE FREED"),
    (63, "SPORT", "LILLE STUN BAYERN 2-1 IN UCL",
     "LIVERPOOL 3-0; BARCA 4-1; PSG 2-2; UTD 2-2"),
    (5, "WAR", "RUSSIA CALLS SHIP STRIKES 'TERRORISM'",
     "MOSCOW - BALTIC, LIBYA STRIKES DENOUNCED"),
    (16, "POLITICS", "SARKOZY, BRUNI ORDERED TO TRIAL",
     "PARIS - HEARING SET FOR APRIL 1, 2027"),
    (32, "BUSINESS", "BRENT OPENS AT $90.97 IN ASIA",
     "LONDON - DOWN 0.5%, 20% IN NOVEMBER"),
    (42, "WORLD", "WFP: CHOKEPOINTS COULD ADD $727M COSTS",
     "NEW YORK - 266M PEOPLE FACE ACUTE HUNGER"),
    (6, "WAR", "UKRAINE: CORVETTE SINKING SELF-DEFENCE",
     "BENGHAZI - KYIV CITES UN CHARTER ARTICLE 51"),
    (19, "POLITICS", "UKRAINE NEEDS 115BN EUROS FOR 2027",
     "KYIV - 90BN COMMITTED; 25BN STILL TO FIND"),
    (35, "BUSINESS", "MICROSOFT DECLARES 'CODE RED' OVERHAUL",
     "REDMOND - AFTER WORST-EVER EXCHANGE OUTAGE"),
    (44, "WORLD", "SANTAS WASH ASHORE IN BULGARIA",
     "BURGAS - FIGURES SPILL FROM CONTAINER"),
    (7, "WAR", "PUTIN VOWS REVENGE FOR REFINERY STRIKES",
     "MOSCOW - RETALIATION PLEDGED"),
    (25, "POLITICS", "GERMANS TURN AGAINST UKRAINE AID",
     "BERLIN - 53% OPPOSE AID, SURVEY FINDS"),
    (36, "BUSINESS", "GARMENT WAGE UP 36% TO $139",
     "DHAKA - 17,000 TAKA; WORKERS SOUGHT DOUBLE"),
    (38, "WORLD", "CNN: CIA, ODNI HIT BY CYBERATTACK",
     "WASHINGTON - ODNI: NO CLASSIFIED DATA HIT"),
    (9, "WAR", "RSF COUNTERINTELLIGENCE CHIEF DEFECTS",
     "KHARTOUM - JABARA SWITCHES TO SUDAN'S ARMY"),
    (11, "WAR", "HORMUZ OIL FLOWS HALVED",
     "HORMUZ - 8.5M BARRELS A DAY, KPLER SAYS"),
]

STORY_COUNT = 1 + 1 + 1 + len(FEATURES) + len(WIRE)
assert STORY_COUNT == 37, STORY_COUNT

# ------------------------------------------------------------ world map ---
# Coarse continent outlines (lon, lat), drawn from general knowledge at
# a scale where only the shapes matter. Equirectangular, lon -180..180,
# lat 75..-60; the panel stretches latitude ~1.27x to fill its box.
# Dots mark the day's datelines; four carry labels.

LAND = [
    # North America
    [(-168, 66), (-156, 71), (-140, 70), (-128, 71), (-115, 73),
     (-100, 73), (-90, 74), (-82, 72), (-75, 72), (-68, 62), (-60, 58),
     (-55, 52), (-60, 47), (-65, 44), (-70, 42), (-74, 39), (-76, 35),
     (-80, 32), (-81, 26), (-80, 25), (-82, 28), (-84, 30), (-88, 29),
     (-91, 29), (-94, 29), (-97, 26), (-97, 22), (-94, 19), (-92, 18),
     (-90, 18), (-87, 21), (-86, 16), (-83, 13), (-80, 9), (-79, 9),
     (-82, 10), (-85, 12), (-87, 13), (-90, 14), (-92, 15), (-95, 16),
     (-97, 16), (-100, 17), (-103, 18), (-106, 20), (-108, 23),
     (-110, 25), (-112, 29), (-114, 31), (-117, 33), (-120, 35),
     (-122, 38), (-124, 41), (-124, 44), (-124, 48), (-127, 50),
     (-130, 54), (-134, 57), (-138, 59), (-143, 60), (-148, 61),
     (-152, 58), (-156, 58), (-160, 55), (-164, 58), (-166, 60)],
    # South America
    [(-80, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12), (-72, -18),
     (-70, -23), (-70, -30), (-68, -38), (-66, -45), (-68, -52),
     (-71, -54), (-68, -50), (-65, -45), (-62, -40), (-58, -35),
     (-52, -32), (-48, -28), (-41, -23), (-39, -15), (-35, -8),
     (-38, -3), (-44, -2), (-50, 0), (-52, 4), (-55, 6), (-58, 8),
     (-62, 9), (-68, 11), (-72, 12), (-75, 10), (-77, 8)],
    # Africa
    [(-17, 15), (-16, 21), (-13, 27), (-9, 31), (-5, 35), (0, 36),
     (6, 37), (11, 37), (15, 32), (20, 32), (25, 31), (30, 31),
     (34, 28), (36, 23), (39, 18), (43, 12), (48, 11), (51, 12),
     (50, 5), (48, 0), (44, -5), (40, -10), (38, -15), (35, -20),
     (33, -26), (30, -30), (27, -33), (22, -35), (18, -32), (15, -27),
     (13, -20), (12, -15), (12, -8), (9, -1), (9, 4), (4, 6), (-2, 5),
     (-8, 5), (-13, 8), (-17, 12)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (0, 51), (3, 53), (8, 57),
     (5, 58), (5, 62), (10, 65), (15, 68), (20, 70), (25, 71), (30, 70),
     (35, 68), (40, 68), (45, 68), (50, 69), (55, 69), (60, 70),
     (65, 72), (70, 73), (75, 74), (80, 73), (85, 74), (90, 75),
     (95, 76), (100, 77), (105, 77), (110, 76), (115, 73), (120, 73),
     (125, 72), (130, 71), (135, 72), (140, 72), (145, 72), (150, 70),
     (155, 69), (160, 70), (165, 66), (170, 66), (175, 65), (178, 65),
     (178, 62), (173, 60), (170, 60), (165, 60), (162, 56), (158, 53),
     (155, 50), (150, 45), (145, 42), (142, 39), (140, 38), (137, 35),
     (135, 34), (132, 33), (130, 33), (127, 35), (124, 38), (122, 38),
     (120, 34), (118, 30), (115, 25), (112, 22), (110, 20), (108, 18),
     (108, 12), (106, 10), (104, 8), (102, 6), (100, 8), (98, 10),
     (97, 15), (95, 16), (93, 18), (91, 22), (89, 22), (87, 21),
     (85, 19), (83, 17), (81, 15), (80, 13), (79, 9), (77, 8), (76, 10),
     (75, 14), (73, 17), (72, 20), (70, 22), (68, 24), (66, 25),
     (64, 25), (62, 25), (60, 25), (58, 26), (58, 24), (59, 22),
     (58, 20), (56, 17), (54, 15), (52, 14), (50, 14), (48, 14),
     (45, 13), (43, 12), (41, 14), (40, 16), (39, 20), (38, 24),
     (37, 27), (35, 29), (34, 31), (35, 33), (36, 36), (34, 36),
     (32, 36), (30, 36), (28, 37), (26, 38), (24, 39), (22, 39),
     (20, 40), (18, 40), (16, 42), (14, 44), (12, 44), (10, 44),
     (8, 44), (6, 43), (4, 43), (2, 42), (0, 40), (-2, 37), (-5, 36),
     (-8, 35)],
    # Australia
    [(114, -22), (118, -20), (122, -14), (126, -14), (132, -12),
     (136, -12), (140, -17), (142, -11), (142, -15), (146, -19),
     (148, -20), (150, -22), (150, -27), (153, -27), (153, -32),
     (150, -37), (146, -39), (140, -38), (136, -35), (132, -32),
     (128, -32), (124, -33), (120, -34), (116, -35), (114, -32),
     (113, -26), (113, -22)],
    # New Guinea, Borneo, Sumatra, UK, Japan (small islands)
    [(131, -1), (136, -2), (141, -3), (146, -6), (147, -8), (143, -8),
     (138, -8), (134, -6), (131, -3)],
    [(109, 1), (113, 4), (117, 6), (119, 1), (117, -3), (112, -3),
     (109, -1)],
    [(95, 5), (98, 3), (101, 0), (104, -3), (106, -5), (103, -5),
     (100, -2), (97, 1), (95, 4)],
    [(-5, 50), (-3, 53), (-1, 55), (-2, 58), (-4, 58), (-5, 55),
     (-6, 52)],
    [(130, 31), (132, 33), (134, 35), (136, 37), (139, 39), (141, 42),
     (140, 44), (138, 42), (135, 38), (132, 34)],
]

# Dots on the map: (lon, lat, label or None, label dx, label dy).
MAP_DOTS = [
    (98, 40, "JIUQUAN", -60, -4),
    (39, 21, "JEDDAH", 6, 6),
    (37, 56, "MOSCOW", 8, -4),
    (149, -35, "CANBERRA", -68, -4),
    (-77, 39, None, 0, 0),
    (0, 51, None, 0, 0),
    (-93, 42, None, 0, 0),
    (31, 46, None, 0, 0),
    (-75, 10, None, 0, 0),
]

DOT_RED = bytes((200, 60, 44))

def draw_map_panel(pg, fx, fy, fw, fh):
    """The 4th feature-row slot: a small world map of the day."""
    pg.rect(fx, fy, fw, fh, CARD)
    pg.frame(fx, fy, fw, fh, INK, 2)
    pg.rect(fx + 12, fy + 12, 9, 9, BEAT["WORLD"])
    pg.text(fx + 27, fy + 11, "WORLD - THE DAY'S MAP", 1.15,
            BEAT["WORLD"], bold=True)
    mx, my, mw, mh = fx + 12, fy + 30, fw - 24, 100
    for poly in LAND:
        pts = [(mx + (lon + 180) / 360.0 * mw,
                my + (75 - lat) / 135.0 * mh) for lon, lat in poly]
        pg.poly(pts, CLOUD)
    pg.frame(mx, my, mw, mh, MUTED, 1)
    for lon, lat, label, dx, dy in MAP_DOTS:
        dxp = mx + (lon + 180) / 360.0 * mw
        dyp = my + (75 - lat) / 135.0 * mh
        pg.rect(dxp - 2.5, dyp - 2.5, 5, 5, INK)
        pg.rect(dxp - 1.5, dyp - 1.5, 3, 3, DOT_RED)
        if label:
            pg.text(dxp + dx, dyp + dy, label, 1.0, INK, bold=True)
    pg.text(fx + 12, fy + 138, "JIUQUAN - JEDDAH", 1.0, MUTED, bold=True)
    pg.text(fx + 12, fy + 150, "MOSCOW - CANBERRA", 1.0, MUTED, bold=True)
    pg.text(fx + 12, fy + 162, "WASHINGTON - LONDON", 1.0, MUTED,
            bold=True)
    pg.text(fx + 12, fy + 174, "IOWA - ODESA - CARTAGENA", 1.0, MUTED,
            bold=True)

# ------------------------------------------------------------ drawing -----

def kicker(pg, x, y, story, s=1.7):
    beat, place = story[1], story[2]
    col = BEAT[beat]
    pg.rect(x, y + 1, 9, 9, col)
    pg.text(x + 15, y, beat + " - " + place, s, col, bold=True)

def chip(pg, x, y, text, s=1.6):
    w = pg.text_w(text, s) + 18
    pg.rect(x, y, w, 24, INK)
    pg.text(x + 9, y + 5, text, s, PAPER, bold=True)
    return w

def scene_space(pg, x, y, w, h):
    """The lead's night-launch scene: stars, Earth arc, rocket, station.
    V3 rework: the straight glow stripes are gone — the atmosphere is a
    faint disc hugging the Earth arc; clouds are horizontal streaks,
    not discs; smoke is a tapered plume; the launch pad sits clear of
    the arc; the station has a truss, mast and a leader line to its
    label; the two caption lines are short and sit in the dark corner
    clear of the arc."""
    pg.rect(x, y, w, h, NIGHT)
    box = (x, y, w, h)
    # Earth: a great disc rising into the strip's foot, rim-lit, with a
    # faint atmospheric halo that follows the arc (not straight bands)
    pg.disc(x + w * 0.34, y + h + 150, 203, GLOW1, clip=box)
    pg.disc(x + w * 0.34, y + h + 150, 196, RIM, clip=box)
    pg.disc(x + w * 0.34, y + h + 150, 193, EARTH, clip=box)
    # cloud streaks on the Earth arc: elongated, low, overlapping discs
    ecx = x + w * 0.34
    for ccx, ccy, ln in ((ecx - 52, y + h - 18, 46),
                         (ecx + 34, y + h - 26, 38),
                         (ecx + 4, y + h - 8, 30)):
        pg.rect(ccx - ln // 2, ccy - 4, ln, 8, CLOUD, )
        pg.disc(ccx - ln // 2 + 4, ccy, 5, CLOUD, clip=box)
        pg.disc(ccx + ln // 2 - 4, ccy, 5, CLOUD, clip=box)
    # deterministic star field (fixed-seed hash, no RNG state)
    for i in range(90):
        sx = x + (i * 137.5) % w
        sy = y + (i * 89.3) % (h - 30)
        r = 2.6 if i % 7 == 0 else (1.9 if i % 3 else 1.1)
        pg.rect(sx, sy, r, r, STAR)
        if i % 11 == 0:
            pg.rect(sx - 3, sy + r / 2 - 0.5, 7, 1, STAR)
            pg.rect(sx + r / 2 - 0.5, sy - 3, 1, 7, STAR)
    # launch pad and tower at the rocket's base, clear of the Earth arc
    pg.rect(x + 14, y + h - 10, 50, 10, PAD)
    pg.rect(x + 18, y + h - 38, 3, 28, PAD)
    # Tiangong station, top right: core + two panel wings + capsule,
    # a truss and mast, and a leader line down to its label
    sx, sy = x + w - 150, y + 6
    pg.rect(sx, sy, 40, 14, STAR)
    pg.rect(sx - 36, sy + 3, 30, 9, RIM)
    pg.rect(sx + 46, sy + 3, 30, 9, RIM)
    pg.rect(sx + 19, sy + 14, 2, 6, STAR)
    pg.rect(sx + 15, sy + 20, 12, 5, bytes((200, 60, 44)))
    pg.rect(sx + 21, sy + 14, 1.5, 4, STAR)
    pg.text(sx - 36, sy + 28, "TIANGONG", 1.1, STAR)
    # rocket climbing toward the station
    ang = math.radians(-52)
    bx, by = x + 56, y + h - 16
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    def pt(along, side):
        return (bx + ux * along + vx * side, by + uy * along + vy * side)
    # smoke plume trailing the nozzle: a tapered cone, down and left
    pg.poly([(bx - ux * 4 + vx * 4, by - uy * 4 + vy * 4),
             (bx - ux * 4 - vx * 4, by - uy * 4 - vy * 4),
             (bx - ux * 42 - vx * 13, by - uy * 42 - vy * 13),
             (bx - ux * 42 + vx * 13, by - uy * 42 + vy * 13)], SMOKE)
    pg.disc(bx - ux * 14, by - uy * 14, 5, SMOKE, clip=box)
    pg.poly([pt(8, -6), pt(-22, 0), pt(8, 6)], FLAME)
    pg.poly([pt(8, -9), pt(58, -9), pt(58, 9), pt(8, 9)], STAR)
    pg.poly([pt(58, -9), pt(80, 0), pt(58, 9)], bytes((200, 60, 44)))
    pg.poly([pt(8, -9), pt(-6, -20), pt(14, -9)], bytes((200, 60, 44)))
    pg.poly([pt(8, 9), pt(-6, 20), pt(14, 9)], bytes((200, 60, 44)))
    # short captions in the dark bottom-right corner, clear of the arc
    pg.text(x + w - 12, y + h - 27, "ALI, 40 - 5-10 DAYS", 1.15, STAR,
            align="right")
    pg.text(x + w - 12, y + h - 12, "LONG MARCH-2F - 08:18", 1.15, STAR,
            align="right")

def draw():
    pg = Page(PAPER)
    M = 26
    TOP = 174
    # -- masthead ---------------------------------------------------------
    pg.text(W / 2, 24, "THE WORLD'S NEWS", 7.2, INK, bold=True,
            align="center")
    pg.text(M, 94, "ONE DAY - ONE PAGE - 37 STORIES", 1.6, MUTED, bold=True)
    pg.text(W - M, 94, "ALL THE NEWS OF ONE WEDNESDAY", 1.6, MUTED,
            bold=True, align="right")
    pg.rect(M, 116, W - 2 * M, 3, INK)
    # -- date band ----------------------------------------------------------
    pg.rect(M, 124, W - 2 * M, 40, INK)
    pg.text(M + 14, 133, "WEDNESDAY 25 NOVEMBER 2026", 2.6, PAPER, bold=True)
    pg.text(W - M - 14, 137, "37 STORIES - SIX BEATS", 1.8, PAPER,
            bold=True, align="right")
    # -- lead ---------------------------------------------------------------
    lx, ly, lw, lh = M, TOP, 574, 334
    pg.rect(lx, ly, lw, lh, CARD)
    pg.frame(lx, ly, lw, lh, INK, 2)
    kicker(pg, lx + 16, ly + 14, LEAD)
    hy = ly + 36
    for ln in pg.wrap(LEAD[3], 2.6, lw - 32):
        pg.text(lx + 16, hy, ln, 2.6, INK, bold=True)
        hy += 26
    scene_space(pg, lx + 16, hy + 6, lw - 32, 96)
    by = hy + 6 + 96 + 6
    pg.para(lx + 16, by, LEAD[4], 1.65, INK, lw - 32, 16)
    chip(pg, lx + 16, ly + lh - 36, LEAD[5])
    # -- right rail: chart + rail feature ----------------------------------
    rx, rw = 616, W - M - 616
    ch_h = 184
    pg.rect(rx, ly, rw, ch_h, CARD)
    pg.frame(rx, ly, rw, ch_h, INK, 2)
    kicker(pg, rx + 14, ly + 12, CHART, 1.6)
    pg.text(rx + 14, ly + 36, "ASIA STOCKS TUMBLE", 2.4, INK, bold=True)
    pg.text(rx + 14, ly + 61, "ON TARIFF THREATS", 2.4, INK, bold=True)
    bx = rx + 120
    bw = rw - 120 - 66
    for i, (name, val) in enumerate(CHART_BARS):
        yy = ly + 94 + i * 20
        pg.text(rx + 14, yy + 1, name, 1.15, MUTED, bold=True)
        bl = bw * abs(val) / 5.3
        pg.rect(bx, yy, bl, 13, BEAT["BUSINESS"])
        pg.text(bx + bl + 7, yy + 1, "-" + str(abs(val)) + "%", 1.3,
                INK, bold=True)
    pg.text(rx + 14, ly + ch_h - 15, "*NIKKEI INTRADAY - ALL FIGURES "
            "WEDNESDAY", 1.0, MUTED)
    ry = ly + ch_h + 12
    rh = ly + lh - ry
    pg.rect(rx, ry, rw, rh, CARD)
    pg.frame(rx, ry, rw, rh, INK, 2)
    kicker(pg, rx + 14, ry + 11, RAIL, 1.4)
    chip(pg, rx + rw - 14 - (pg.text_w(RAIL[5], 1.3) + 18), ry + 8,
         RAIL[5], 1.3)
    yy = ry + 33
    for ln in pg.wrap(RAIL[3], 1.85, rw - 28):
        pg.text(rx + 14, yy, ln, 1.85, INK, bold=True)
        yy += 18
    pg.para(rx + 14, yy + 3, RAIL[4], 1.35, INK, rw - 28, 13.5)
    # -- feature row: 3 features + the world map panel ----------------------
    fy, fh, gap = 520, 198, 12
    fw = (W - 2 * M - 3 * gap) / 4.0
    for i in range(4):
        fx = M + i * (fw + gap)
        if i == 3:
            draw_map_panel(pg, fx, fy, fw, fh)
            continue
        st = FEATURES[i]
        pg.rect(fx, fy, fw, fh, CARD)
        pg.frame(fx, fy, fw, fh, INK, 2)
        kicker(pg, fx + 12, fy + 11, st, 1.2)
        yy = fy + 34
        for ln in pg.wrap(st[3], 1.55, fw - 24):
            pg.text(fx + 12, yy, ln, 1.55, INK, bold=True)
            yy += 16
        pg.para(fx + 12, yy + 2, st[4], 1.25, INK, fw - 24, 12.5)
        chip(pg, fx + 12, fy + fh - 33, st[5], 1.3)
    # -- the wire -------------------------------------------------------------
    wy = 728
    pg.rect(M, wy - 6, W - 2 * M, 3, INK)
    pg.text(M, wy + 4, "THE WIRE - 31 MORE STORIES FROM THE DAY", 1.9,
            INK, bold=True)
    pg.text(W - M, wy + 6, "AS REPORTED ON THE DAY", 1.4, MUTED,
            bold=True, align="right")
    cols, rows = 3, 11
    gx, gy = M, wy + 34
    cw = (W - 2 * M - (cols - 1) * 18) / cols
    chh = 21
    for idx, st in enumerate(WIRE):
        cx = gx + (idx % cols) * (cw + 18)
        cy = gy + (idx // cols) * chh
        col = BEAT[st[1]]
        pg.rect(cx, cy + 1.5, 6.5, 6.5, col)
        hs = pg.fit_scale(st[2], 1.15, cw - 12, floor=0.90)
        pg.text(cx + 12, cy, st[2], hs, INK, bold=True)
        bs = pg.fit_scale(st[3], 0.95, cw - 12, floor=0.80)
        pg.text(cx + 12, cy + 11.5, st[3], bs, MUTED)
    # -- footer ---------------------------------------------------------------
    fy2 = 996
    pg.rect(M, fy2, W - 2 * M, 22, INK)
    pg.text(W / 2, fy2 + 5, "SOURCES: REUTERS, AP, AFP, XINHUA, WHO, "
            "UEFA, BEA, EPA, KPLER, CONF. BOARD", 1.35, PAPER, bold=True,
            align="center")
    return pg

# --------------------------------------------------------------- output ---

def png_bytes(rgb):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            chunk(b"IEND", b""))

def main():
    pg = draw()
    data = png_bytes(pg.finish())
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "entry.png"), "wb") as fh:
        fh.write(data)

if __name__ == "__main__":
    main()
