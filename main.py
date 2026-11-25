# news-image-20261125 — main.py
#
# A one-page broadsheet that sums up the world's news of Wednesday
# 25 November 2026 in a single image. Python 3.13, standard library only,
# no network. The program draws the page itself (its own tiny rasteriser,
# its own 5x7 type, its own PNG writer) and writes /output/entry.png.
# It runs twice and writes identical bytes: every drawing decision is
# integer or fixed-seed arithmetic, nothing reads a clock or a RNG.
#
# Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for /output:
#   mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
#
# The page carries exactly 37 stories from that day's reporting
# (Reuters, AP, AFP, Xinhua, WHO, UEFA and official releases):
#   1 lead, 1 markets chart panel, 1 feature in the rail,
#   4 features in a row, and 30 one-line wire briefs.

import math
import os
import struct
import zlib

# ---------------------------------------------------------------- type ----
# A 5x7 pixel typeface, drawn as data: seven rows of five bits per glyph.
# Only the characters the page prints are defined; text is upper-case.

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "10001", "11001", "10101", "10011", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
}

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
        return len(clean(text)) * 6 * s - s

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
            for r in range(7):
                rowbits = glyph[r]
                for c in range(5):
                    if rowbits[c] == "1":
                        self.rect(x + c * s, y + r * s, s + thick, s, rgb)
            x += 6 * s
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

    def fit_scale(self, text, s, width):
        """Largest scale at or below s (step 0.05) that fits the width."""
        while s > 0.9 and self.text_w(text, s) > width:
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
        "be targeted if Hodeidah is attacked; the coalition then "
        "struck targets at Hodeidah.",
        "JEDDAH THREATENED")

FEATURES = [
    (8, "WAR", "MOSCOW",
     "RUSSIA'S WAR DEAD PASS 490,000 CONFIRMED",
     "Breached-data count: 490,000 registered deaths confirmed; "
     "estimates 700,000.",
     "AT LEAST 490,000 DEAD"),
    (36, "BUSINESS", "DHAKA",
     "GARMENT WAGE UP 36% TO $139",
     "Garment minimum wage up 36% to 17,000 taka ($139) after protests, "
     "from December 1.",
     "+36% TO $139"),
    (15, "POLITICS", "CANBERRA",
     "AUSTRALIA, SOLOMONS SIGN SECURITY TREATY",
     "Australia becomes the Solomons' primary security partner; no "
     "foreign base allowed.",
     "PARTNER OF CHOICE"),
    (38, "WORLD", "WASHINGTON",
     "CIA, ODNI HIT BY CYBERATTACK",
     "CNN reports intrusion at CIA/ODNI analysis system; ODNI says no "
     "classified data hit.",
     "CYBER INTRUSION"),
]

# Wire briefs: (pool, beat, headline, one terse line). 30 of them.
WIRE = [
    (2, "WAR", "DRONE HITS RIYADH'S TALLEST TOWER AGAIN",
     "RIYADH - PIF TOWER STRUCK; AT LEAST 11 WOUNDED"),
    (3, "WAR", "HOUTHIS CLOSE TO 60 KM OF ADEN",
     "ADEN - SOUTHERN PORT 'WILL NOT FALL', ARMY SAYS"),
    (4, "WAR", "RUSSIAN STRIKE ON ODESA KILLS TWO",
     "ODESA - TWO DEAD, THREE HURT; KYIV DRONE ATTACK"),
    (5, "WAR", "RUSSIA CALLS SHIP STRIKES 'TERRORISM'",
     "MOSCOW - BALTIC, LIBYA VESSEL STRIKES DENOUNCED"),
    (6, "WAR", "UKRAINE: CORVETTE SINKING WAS SELF-DEFENCE",
     "BENGHAZI - KYIV CITES UN CHARTER ARTICLE 51"),
    (7, "WAR", "PUTIN VOWS REVENGE FOR REFINERY STRIKES",
     "MOSCOW - RETALIATION PLEDGED OVER OIL STRIKES"),
    (9, "WAR", "RSF COUNTERINTELLIGENCE CHIEF DEFECTS",
     "KHARTOUM - JABARA SWITCHES TO SUDAN'S ARMY"),
    (11, "WAR", "HORMUZ OIL FLOWS HALVED",
     "HORMUZ - 8.5M BARRELS A DAY, TRACKER KPLER SAYS"),
    (12, "POLITICS", "TRUMP READIES NEW TARIFF WAVE",
     "WASHINGTON - 'EXCESS CAPACITY' PROBE, 16 PARTNERS"),
    (13, "POLITICS", "HUAWEI CONVICTED IN NEW YORK COURT",
     "NEW YORK - GUILTY ON 10 OF 12 COUNTS; WILL APPEAL"),
    (14, "POLITICS", "SHANGHAI CHIEF UNDER GRAFT PROBE",
     "SHANGHAI - CHEN JINING, FOURTH TOP PROBE SINCE 2025"),
    (16, "POLITICS", "SARKOZY, BRUNI ORDERED TO TRIAL",
     "PARIS - PRE-TRIAL HEARING SET FOR APRIL 1, 2027"),
    (19, "POLITICS", "UKRAINE NEEDS 115BN EUROS FOR 2027",
     "KYIV - 90BN EUROS COMMITTED; 25BN STILL TO FIND"),
    (25, "POLITICS", "GERMANS TURN AGAINST UKRAINE AID",
     "BERLIN - 53% NOW OPPOSE MILITARY AID, SURVEY FINDS"),
    (29, "BUSINESS", "NVIDIA SLIDES AS HYPE FADES",
     "NEW YORK - NVIDIA -5.9% TUESDAY; DOW ROSE 0.9%"),
    (30, "BUSINESS", "CONSUMER CONFIDENCE JUMPS TO 103.3",
     "NEW YORK - UP 11.4 POINTS, HIGHEST SINCE JAN 2025"),
    (31, "BUSINESS", "BITCOIN SLIPS BELOW $60,000",
     "NEW YORK - $59,257.71; RECORD $4.71BN ETF OUTFLOW"),
    (32, "BUSINESS", "BRENT OPENS AT $90.97 IN ASIA",
     "LONDON - DOWN 0.5% ON THE DAY, 20% IN NOVEMBER"),
    (35, "BUSINESS", "MICROSOFT DECLARES 'CODE RED' OVERHAUL",
     "REDMOND - AFTER WORST-EVER EXCHANGE OUTAGE"),
    (37, "WORLD", "ARMY SET TO DETONATE 9,500 POUNDS",
     "IOWA - LEAD AZIDE IN 68 BARRELS; STAY INDOORS"),
    (39, "WORLD", "WHO EVACUATES HOSPITAL AMID FIGHTING",
     "ITURI - EBOLA TOLL STANDS AT 5,775 DEATHS"),
    (41, "WORLD", "25 HELD HOSTAGE IN SUPERMARKET",
     "CARTAGENA - FAILED ARMOURED-CAR HIJACK; FIVE FREED"),
    (42, "WORLD", "WFP: CHOKEPOINTS COULD ADD $727M COSTS",
     "NEW YORK - 266M PEOPLE FACE ACUTE HUNGER"),
    (44, "WORLD", "SANTAS WASH ASHORE IN BULGARIA",
     "BURGAS - LIFE-SIZE FIGURES SPILL FROM CONTAINER"),
    (45, "WORLD", "TRUMP PARDONS TURKEYS FREEDOM, FEATHERS",
     "WASHINGTON - THANKSGIVING PARDON AT WHITE HOUSE"),
    (48, "SCIENCE", "OLDEST QUASAR SEEN 13.1 BILLION YEARS BACK",
     "SPACE - EUCLID FIND; BLACK HOLE 360M SUNS"),
    (49, "SCIENCE", "TITANIUM OXIDE FOUND AROUND YOUNG STAR",
     "SPACE - ALMA READS ORION SOURCE I'S AIR"),
    (52, "SPORT", "MADRID ROUT PSV 5-1",
     "MADRID - MBAPPE TWICE; FIVE WINS FROM FIVE IN UCL"),
    (53, "SPORT", "ARSENAL HELD 1-1 AT DORTMUND",
     "DORTMUND - CHAMPIONS LEAGUE POINT SHARED"),
    (56, "SPORT", "ENGLAND LEVEL T20 SERIES IN AUSTRALIA",
     "GOLD COAST - DONALD 85 OFF 32; SERIES 1-1"),
]

STORY_COUNT = 1 + 1 + 1 + len(FEATURES) + len(WIRE)
assert STORY_COUNT == 37, STORY_COUNT

# ------------------------------------------------------------ drawing -----

def kicker(pg, x, y, story, s=2.0):
    beat, place = story[1], story[2]
    col = BEAT[beat]
    pg.rect(x, y + 1, 9, 9, col)
    pg.text(x + 15, y, beat + " - " + place, s, col, bold=True)

def chip(pg, x, y, text, s=1.9):
    w = pg.text_w(text, s) + 18
    pg.rect(x, y, w, 24, INK)
    pg.text(x + 9, y + 5, text, s, PAPER, bold=True)
    return w

def scene_space(pg, x, y, w, h):
    """The lead's night-launch scene: stars, Earth arc, rocket, station."""
    pg.rect(x, y, w, h, NIGHT)
    box = (x, y, w, h)
    # Earth: a great disc rising into the strip's foot, rim-lit
    pg.disc(x + w * 0.34, y + h + 150, 196, RIM, clip=box)
    pg.disc(x + w * 0.34, y + h + 150, 193, EARTH, clip=box)
    # deterministic star field (fixed-seed hash, no RNG state)
    for i in range(90):
        sx = x + (i * 137.5) % w
        sy = y + (i * 89.3) % (h - 30)
        r = 1.1 if i % 3 else 1.9
        pg.rect(sx, sy, r, r, STAR)
    # Tiangong station, top right: core + two panel wings
    sx, sy = x + w - 150, y + 13
    pg.rect(sx, sy, 40, 14, STAR)
    pg.rect(sx - 36, sy + 3, 30, 9, RIM)
    pg.rect(sx + 46, sy + 3, 30, 9, RIM)
    pg.text(sx - 36, sy + 20, "TIANGONG", 1.3, STAR)
    # rocket climbing toward the station
    ang = math.radians(-52)
    bx, by = x + 56, y + h - 16
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    def pt(along, side):
        return (bx + ux * along + vx * side, by + uy * along + vy * side)
    pg.poly([pt(8, -6), pt(-22, 0), pt(8, 6)], FLAME)
    pg.poly([pt(8, -9), pt(58, -9), pt(58, 9), pt(8, 9)], STAR)
    pg.poly([pt(58, -9), pt(80, 0), pt(58, 9)], bytes((200, 60, 44)))
    pg.poly([pt(8, -9), pt(-6, -20), pt(14, -9)], bytes((200, 60, 44)))
    pg.poly([pt(8, 9), pt(-6, 20), pt(14, 9)], bytes((200, 60, 44)))
    pg.text(x + w - 12, y + h - 32, "08:18 CST - LONG MARCH-2F", 1.35,
            STAR, align="right")
    pg.text(x + w - 12, y + h - 17,
            "ALI, 40, PAYLOAD SPECIALIST - STAYS 5-10 DAYS", 1.35, STAR,
            align="right")

def draw():
    pg = Page(PAPER)
    M = 26
    TOP = 184
    # -- masthead ---------------------------------------------------------
    pg.text(W / 2, 26, "THE WORLD'S NEWS", 9.5, INK, bold=True,
            align="center")
    pg.text(M, 96, "ONE DAY - ONE PAGE - 37 STORIES", 1.9, MUTED, bold=True)
    pg.text(W - M, 96, "ALL THE NEWS OF ONE WEDNESDAY", 1.9, MUTED,
            bold=True, align="right")
    pg.rect(M, 122, W - 2 * M, 3, INK)
    # -- date band ----------------------------------------------------------
    pg.rect(M, 132, W - 2 * M, 44, INK)
    pg.text(M + 14, 142, "WEDNESDAY 25 NOVEMBER 2026", 3.4, PAPER, bold=True)
    pg.text(W - M - 14, 146, "37 STORIES - SIX BEATS", 2.2, PAPER,
            bold=True, align="right")
    # -- lead ---------------------------------------------------------------
    lx, ly, lw, lh = M, TOP, 574, 348
    pg.rect(lx, ly, lw, lh, CARD)
    pg.frame(lx, ly, lw, lh, INK, 2)
    kicker(pg, lx + 16, ly + 14, LEAD)
    hy = ly + 38
    for ln in pg.wrap(LEAD[3], 4.3, lw - 32):
        pg.text(lx + 16, hy, ln, 4.3, INK, bold=True)
        hy += 37
    scene_space(pg, lx + 16, hy + 6, lw - 32, 78)
    by = hy + 92
    pg.para(lx + 16, by, LEAD[4], 1.95, INK, lw - 32, 18)
    chip(pg, lx + 16, ly + lh - 36, LEAD[5])
    # -- right rail: chart + rail feature ----------------------------------
    rx, rw = 616, W - M - 616
    ch_h = 184
    pg.rect(rx, ly, rw, ch_h, CARD)
    pg.frame(rx, ly, rw, ch_h, INK, 2)
    kicker(pg, rx + 14, ly + 12, CHART, 1.9)
    pg.text(rx + 14, ly + 38, "ASIA STOCKS TUMBLE", 2.9, INK, bold=True)
    pg.text(rx + 14, ly + 63, "ON TARIFF THREATS", 2.9, INK, bold=True)
    bx = rx + 112
    bw = rw - 112 - 58
    for i, (name, val) in enumerate(CHART_BARS):
        yy = ly + 94 + i * 20
        pg.text(rx + 14, yy + 1, name, 1.5, MUTED, bold=True)
        bl = bw * abs(val) / 5.3
        pg.rect(bx, yy, bl, 13, BEAT["BUSINESS"])
        pg.text(bx + bl + 7, yy + 1, "-" + str(abs(val)) + "%", 1.5,
                INK, bold=True)
    pg.text(rx + 14, ly + ch_h - 15, "*NIKKEI INTRADAY - MSCI APAC "
            "EX-JAPAN", 1.2, MUTED)
    ry = ly + ch_h + 12
    rh = ly + lh - ry
    pg.rect(rx, ry, rw, rh, CARD)
    pg.frame(rx, ry, rw, rh, INK, 2)
    kicker(pg, rx + 14, ry + 11, RAIL, 1.9)
    yy = ry + 35
    for ln in pg.wrap(RAIL[3], 2.15, rw - 28):
        pg.text(rx + 14, yy, ln, 2.15, INK, bold=True)
        yy += 20
    pg.para(rx + 14, yy + 3, RAIL[4], 1.55, INK, rw - 28, 15)
    # -- feature row ---------------------------------------------------------
    fy, fh, gap = 546, 210, 12
    fw = (W - 2 * M - 3 * gap) / 4.0
    for i, st in enumerate(FEATURES):
        fx = M + i * (fw + gap)
        pg.rect(fx, fy, fw, fh, CARD)
        pg.frame(fx, fy, fw, fh, INK, 2)
        kicker(pg, fx + 12, fy + 11, st, 1.45)
        yy = fy + 36
        for ln in pg.wrap(st[3], 2.1, fw - 24):
            pg.text(fx + 12, yy, ln, 2.1, INK, bold=True)
            yy += 19.5
        pg.para(fx + 12, yy + 2, st[4], 1.5, INK, fw - 24, 14.5)
        chip(pg, fx + 12, fy + fh - 33, st[5], 1.5)
    # -- the wire -------------------------------------------------------------
    wy = 768
    pg.rect(M, wy - 6, W - 2 * M, 3, INK)
    pg.text(M, wy + 4, "THE WIRE - 30 MORE STORIES FROM THE DAY", 2.1,
            INK, bold=True)
    pg.text(W - M, wy + 6, "AS REPORTED ON THE DAY", 1.6, MUTED,
            bold=True, align="right")
    cols, rows = 3, 10
    gx, gy = M, wy + 34
    cw = (W - 2 * M - (cols - 1) * 18) / cols
    chh = 18.4
    for idx, st in enumerate(WIRE):
        cx = gx + (idx % cols) * (cw + 18)
        cy = gy + (idx // cols) * chh
        col = BEAT[st[1]]
        pg.rect(cx, cy + 1.5, 6.5, 6.5, col)
        hs = pg.fit_scale(st[2], 1.45, cw - 12)
        pg.text(cx + 12, cy, st[2], hs, INK, bold=True)
        bs = pg.fit_scale(st[3], 1.05, cw - 12)
        pg.text(cx + 12, cy + 10.8, st[3], bs, MUTED)
    # -- footer ---------------------------------------------------------------
    fy2 = 988
    pg.rect(M, fy2, W - 2 * M, 26, INK)
    pg.text(W / 2, fy2 + 6, "WEDNESDAY 25 NOVEMBER 2026 - SOURCES: REUTERS, "
            "AP, AFP, XINHUA, WHO, UEFA", 1.55, PAPER, bold=True,
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
