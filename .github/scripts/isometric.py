"""Draw an isometric contribution calendar (light + dark SVG) for the profile README.

Runs daily from .github/workflows/isometric.yml. Standard library only.

  python isometric.py                 # fetch live data with $GITHUB_TOKEN
  python isometric.py --data f.json   # use a saved calendar (for previews)
"""
import base64, json, math, os, sys, urllib.request
from datetime import date, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets")
USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "Laihu08")

THEMES = {
    "light": dict(bg="#f5f5f5", line="rgba(13,13,13,0.10)", ink="#2b2b2b", mute="#5f5f5f", faint="#707070",
                  levels=["#e6e6e6", "#c2c2c2", "#8f8f8f", "#575757", "#262626"]),
    "dark": dict(bg="#121315", line="rgba(255,255,255,0.12)", ink="#ededed", mute="#a3a3a3", faint="#8c8c8c",
                 levels=["#28292d", "#4a4b50", "#7a7b80", "#b4b5b9", "#f0f0f0"]),
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
  totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def font_face(name, file):
    b64 = base64.b64encode(open(os.path.join(ROOT, "assets/fonts", file), "rb").read()).decode()
    return f"@font-face{{font-family:{name};src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def shade(hex_, f):
    n = int(hex_[1:], 16)
    r, g, b = (n >> 16) & 255, (n >> 8) & 255, n & 255
    return "#%02x%02x%02x" % (round(r * f), round(g * f), round(b * f))


def stats(days):
    counts = [d["contributionCount"] for d in days]
    best = max(days, key=lambda d: d["contributionCount"])
    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c else 0
        longest = max(longest, cur)
    current = 0
    for c in reversed(counts[:-1] if counts and counts[-1] == 0 else counts):  # today may still be empty
        if not c:
            break
        current += 1
    return best, longest, current


def render(cal, theme):
    t = THEMES[theme]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    total = cal["totalContributions"]
    peak = max(d["contributionCount"] for d in days) or 1
    best, longest, current = stats(days)

    W, H = 1200, 720
    s = 17.0                               # cell size
    cos, sin = math.cos(math.pi / 6), math.sin(math.pi / 6)
    ox, oy, zmax = 210, 150, 110           # origin of week 0 / Sunday, tallest bar

    def P(x, y, z=0.0):
        return (ox + (x - y) * cos * s, oy + (x + y) * sin * s - z)

    def poly(pts, fill):
        return '<polygon points="%s" fill="%s"/>' % (" ".join("%.1f,%.1f" % p for p in pts), fill)

    cells = []
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            wd = (date.fromisoformat(d["date"]).weekday() + 1) % 7   # Sunday = 0
            cells.append((wi, wd, d))
    cells.sort(key=lambda c: (c[0] + c[1], c[0]))

    g = 0.84
    out = []
    for x, y, d in cells:
        v = d["contributionCount"]
        base = t["levels"][LEVEL.get(d["contributionLevel"], 0)]
        h = 4 + (v / peak) ** 0.85 * zmax if v else 2
        A, B, C, D = P(x, y, h), P(x + g, y, h), P(x + g, y + g, h), P(x, y + g, h)
        B0, C0, D0 = P(x + g, y), P(x + g, y + g), P(x, y + g)
        out.append(poly([D, C, C0, D0], shade(base, 0.82)))
        out.append(poly([C, B, B0, C0], shade(base, 0.68)))
        out.append(poly([A, B, C, D], base))

    def text(x, y, s_, fam, size, fill, anchor="start", ls=0):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" fill="{fill}" '
                f'text-anchor="{anchor}" letter-spacing="{ls}">{s_}</text>')

    # month labels along the front edge
    last = None
    for wi, w in enumerate(weeks[:-1]):
        m = date.fromisoformat(w["contributionDays"][0]["date"])
        if m.month != last:
            last = m.month
            px, py = P(wi, 7.7)
            out.append(text(px - 4, py + 12, m.strftime("%b"), "JB", 11, t["faint"], "end"))

    first = date.fromisoformat(days[0]["date"])
    last_d = date.fromisoformat(days[-1]["date"])
    fmt = lambda d_: f"{d_.day} {d_.strftime('%b')}"

    # top-right: heading + stats
    rx = 690
    head = [
        text(rx, 92, f"CONTRIBUTIONS · {first.strftime('%b %Y').upper()} – {last_d.strftime('%b %Y').upper()}", "JB", 12, t["faint"], ls=2),
        text(rx, 168, f"{total:,}", "SG", 64, t["ink"], ls=-1.5),
        text(rx, 196, "contributions in the last year", "PR", 15, t["mute"]),
    ]
    sy = 236
    head.append(f'<line x1="{rx}" y1="{sy}" x2="{W - 70}" y2="{sy}" stroke="{t["line"]}"/>')
    cols = [(f"{best['contributionCount']}", f"Best day · {fmt(date.fromisoformat(best['date']))}"),
            (f"{longest} days", "Longest streak"),
            (f"{current} days", "Current streak")]
    cw = (W - 70 - rx) / 3
    for i, (big, small) in enumerate(cols):
        cx = rx + i * cw + (0 if i == 0 else 18)
        if i:
            head.append(f'<line x1="{rx + i * cw}" y1="{sy + 16}" x2="{rx + i * cw}" y2="{sy + 76}" stroke="{t["line"]}"/>')
        head.append(text(cx, sy + 48, big, "SG", 28, t["ink"]))
        head.append(text(cx, sy + 70, small, "PR", 12.5, t["mute"]))

    # bottom-left: legend
    lx, ly = 70, H - 70
    legend = [text(lx, ly + 11, "Less", "JB", 11, t["faint"])]
    for i, c in enumerate(t["levels"]):
        legend.append(f'<rect x="{lx + 44 + i * 18}" y="{ly}" width="13" height="13" rx="3" fill="{c}"/>')
    legend.append(text(lx + 44 + 5 * 18 + 6, ly + 11, "More", "JB", 11, t["faint"]))

    css = font_face("SG", "space-grotesk-600.woff2") + font_face("PR", "poppins-400.woff2") + font_face("JB", "jetbrains-mono-400.woff2")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="Isometric contribution calendar: {total} contributions in the last year">'
            f"<style>{css}</style>"
            f'<rect width="{W}" height="{H}" rx="16" fill="{t["bg"]}"/>'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="{t["line"]}"/>'
            + "".join(out) + "".join(head) + "".join(legend) + "</svg>")


def main():
    if "--data" in sys.argv:
        cal = json.load(open(sys.argv[sys.argv.index("--data") + 1]))
    else:
        cal = fetch()
    for theme in THEMES:
        with open(os.path.join(OUT, f"isometric-{theme}.svg"), "w") as f:
            f.write(render(cal, theme))
    print(f"isometric calendar written: {cal['totalContributions']} contributions")


if __name__ == "__main__":
    main()
