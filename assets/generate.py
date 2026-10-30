"""Generate profile SVGs (header + project cards) in light and dark, matching the portfolio style."""
import base64, io, sys, os
from xml.sax.saxutils import escape
from fontTools.ttLib import TTFont
from fontTools import subset

OUT = sys.argv[1]
FD = os.path.join(os.path.dirname(__file__), "fonts/node_modules/@fontsource")
FONTS = {
    "disp": f"{FD}/space-grotesk/files/space-grotesk-latin-600-normal.woff2",
    "sans": f"{FD}/poppins/files/poppins-latin-300-normal.woff2",
    "sans4": f"{FD}/poppins/files/poppins-latin-400-normal.woff2",
    "mono": f"{FD}/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff2",
}
FAMILY = {"disp": "SG", "sans": "PL", "sans4": "PR", "mono": "JB"}

THEMES = {
    "light": dict(paper="#f5f5f5", card="#ffffff", ink="#2b2b2b", ink2="#3a3a3a", mute="#5f5f5f", faint="#707070", line="rgba(13,13,13,0.10)", chip="#f5f5f5"),
    "dark": dict(paper="#121315", card="#1b1c1f", ink="#ededed", ink2="#d2d2d2", mute="#a3a3a3", faint="#8c8c8c", line="rgba(255,255,255,0.12)", chip="#232428"),
}

_tt = {k: TTFont(v) for k, v in FONTS.items()}

def width(text, font, size):
    f = _tt[font]; cmap = f.getBestCmap(); hmtx = f["hmtx"]; upm = f["head"].unitsPerEm
    return sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in text) * size / upm

def font_css(used):
    """used: {font_key: set_of_chars} -> @font-face rules with subset, base64 woff2."""
    css = []
    for key, chars in used.items():
        opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["kern", "liga"]
        f = TTFont(FONTS[key]); s = subset.Subsetter(opts); s.populate(text="".join(chars) + " "); s.subset(f)
        buf = io.BytesIO(); f.flavor = "woff2"; f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        css.append(f"@font-face{{font-family:{FAMILY[key]};src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    return "".join(css)

class SVG:
    def __init__(s, w, h, label):
        s.w, s.h, s.label, s.body, s.used = w, h, label, [], {}
    def text(s, x, y, t, font, size, fill, anchor="start", ls=0):
        s.used.setdefault(font, set()).update(t)
        s.body.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}">{escape(t)}</text>')
    def raw(s, r): s.body.append(r)
    def out(s):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s.w} {s.h}" width="{s.w}" height="{s.h}" role="img" aria-label="{escape(s.label)}">'
                f'<style>{font_css(s.used)}</style>' + "".join(s.body) + "</svg>")

PATENT = ('<g transform="translate({x},{y}) scale({k})" fill="none" stroke="{c}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">'
          '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h4"/><path d="M14 2v6h6"/><path d="M14 2l6 6v3"/><path d="M8 13h4"/><path d="M8 17h2"/>'
          '<circle cx="17" cy="16" r="3"/><path d="m15.5 18.7-.7 3.3 2.2-1.2 2.2 1.2-.7-3.3"/></g>')

def header(th):
    W, H = 1200, 400; s = SVG(W, H, "Rahul Selvaraj, Senior AI Engineer")
    s.raw(f'<rect width="{W}" height="{H}" rx="16" fill="{th["paper"]}"/>')
    s.raw(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="15.5" fill="none" stroke="{th["line"]}"/>')
    s.text(W/2, 132, "Rahul Selvaraj", "disp", 84, th["ink"], "middle", -2.2)
    s.text(W/2, 184, "Senior AI Engineer", "sans", 28, th["mute"], "middle")
    s.text(W/2, 222, "AGENTIC AI  ·  FULL-STACK AI SYSTEMS  ·  CLOUD", "mono", 13, th["faint"], "middle", 2.2)
    # stats strip, like the portfolio hero
    top, bot = 262, 360; cw = 250; x0 = W/2 - cw
    s.raw(f'<line x1="{x0}" y1="{top}" x2="{x0+2*cw}" y2="{top}" stroke="{th["line"]}"/>')
    s.raw(f'<line x1="{x0}" y1="{bot}" x2="{x0+2*cw}" y2="{bot}" stroke="{th["line"]}"/>')
    s.raw(f'<line x1="{W/2}" y1="{top}" x2="{W/2}" y2="{bot}" stroke="{th["line"]}"/>')
    s.text(x0 + cw/2, 322, "5+", "disp", 44, th["ink"], "middle")
    s.text(x0 + cw/2, 346, "Years of experience", "sans4", 14, th["mute"], "middle")
    nw = width("2", "disp", 44); icon = 38; gap = 10; total = nw + gap + icon
    cx = W/2 + cw/2; sx = cx - total/2
    s.text(sx, 322, "2", "disp", 44, th["ink"])
    s.raw(PATENT.format(x=sx + nw + gap, y=288, k=icon/24, c=th["ink"]))
    s.text(cx, 346, "International patents", "sans4", 14, th["mute"], "middle")
    return s.out()

def wrap(t, font, size, maxw):
    lines, cur = [], ""
    for w in t.split():
        nxt = (cur + " " + w).strip()
        if width(nxt, font, size) <= maxw: cur = nxt
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

def card(th, p):
    W, H = 580, 300; pad = 32; s = SVG(W, H, p["title"])
    s.raw(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="{th["card"]}" stroke="{th["line"]}"/>')
    s.text(pad, 50, p["tag"].upper(), "mono", 11.5, th["faint"], ls=1.8)
    y = 92
    for ln in wrap(p["title"], "disp", 26, W - 2*pad):
        s.text(pad, y, ln, "disp", 26, th["ink"], ls=-0.4); y += 32
    y = max(y - 6, 120)
    for ln in wrap(p["blurb"], "sans", 14.5, W - 2*pad)[:2]:
        s.text(pad, y, ln, "sans", 14.5, th["mute"]); y += 22
    # pipeline chips with arrows
    fy = H - 92; x = pad; fs = 12; ch = 30
    for i, step in enumerate(p["flow"]):
        tw = width(step, "mono", fs) + 22
        if x + tw > W - pad: x = pad; fy += ch + 10
        s.raw(f'<rect x="{x:.1f}" y="{fy}" width="{tw:.1f}" height="{ch}" rx="7" fill="{th["chip"]}" stroke="{th["line"]}"/>')
        s.text(x + 11, fy + 19.5, step, "mono", fs, th["ink2"])
        x += tw
        if i < len(p["flow"]) - 1:
            s.text(x + 10, fy + 20, "→", "mono", 13, th["faint"], "middle"); x += 20
    s.text(pad, H - 22, p.get("cta", "View on GitHub →"), "sans4", 13, th["ink"] if p.get("url") else th["faint"])
    return s.out()

PROJECTS = [
    dict(slug="multi-agent", tag="Personal / Research", title="LLM Multi-Agent Planning System",
         blurb="Agentic orchestration across GPT, Claude, LLaMA 2 and Mistral, with RAG and vector databases for long-context planning.",
         flow=["Task", "Orchestrator", "LLM agents", "RAG + vector DB", "Plan"], cta="Research project"),
    dict(slug="depth-completion", tag="M.Sc. Thesis", title="Self-Supervised Depth Completion for 3D Object Detection",
         blurb="Fuses sparse LiDAR and RGB into dense depth maps. Improved RMSE, MAE and AP on KITTI.",
         flow=["LiDAR + RGB", "Depth completion", "Dense depth", "3D detection"], url=1),
    dict(slug="rag-chatbot", tag="Personal Project", title="LLM RAG Chatbot",
         blurb="Answers from a knowledge base with RAG on ChromaDB. Runs fully local on Mistral 7B via Ollama, or on OpenAI GPT.",
         flow=["Query", "Embedding", "ChromaDB", "Mistral / GPT", "Streamlit"], url=1),
    dict(slug="hybrid-cag-rag", tag="Personal Project", title="Hybrid AI Chatbot (CAG + RAG)",
         blurb="Cache-augmented generation for fast answers, retrieval-augmented generation for fresh data.",
         flow=["Query", "Cache hit? (CAG)", "Retrieve (RAG)", "Answer"], url=1),
]

os.makedirs(OUT, exist_ok=True)
for name, th in THEMES.items():
    open(f"{OUT}/header-{name}.svg", "w").write(header(th))
    for p in PROJECTS:
        open(f"{OUT}/card-{p['slug']}-{name}.svg", "w").write(card(th, p))
print("done", sorted(os.listdir(OUT)))
