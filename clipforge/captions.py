"""Word-level captions -> ASS (styles, active-word highlight)."""

SENT = (".", "?", "!")


def _bgr(hexcol, alpha=0):
    h = hexcol.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


# mode: "phrase" (2-4 words on screen, spoken word highlighted) or "word" (one word at a time)
# mv: distance of the text from the bottom edge (px on a 1920-high canvas); scale_active: grow the spoken word (%)
# glow: soft glow around letters; box: dark box behind the text
TEMPLATES = {
    "yellow_pop": dict(font="Arial", size=86, bold=1, primary="#FFFFFF", active="#FFE600", outline="#000000", ow=7,
                       shadow=2, box=False, upper=True, pop=True, mode="phrase", mv=470, scale_active=0, glow=0),
    "bold_white": dict(font="Arial", size=86, bold=1, primary="#FFFFFF", active="#FFFFFF", outline="#000000", ow=7,
                       shadow=2, box=False, upper=True, pop=True, mode="phrase", mv=470, scale_active=0, glow=0),
    "karaoke_green": dict(font="Arial", size=84, bold=1, primary="#FFFFFF", active="#39FF88", outline="#0B2A18", ow=8,
                          shadow=2, box=False, upper=True, pop=False, mode="phrase", mv=470, scale_active=0, glow=0),
    "hype_scale": dict(font="Arial", size=80, bold=1, primary="#FFFFFF", active="#FF3B5C", outline="#000000", ow=7,
                       shadow=3, box=False, upper=True, pop=False, mode="phrase", mv=700, scale_active=125, glow=0),
    "neon": dict(font="Arial", size=84, bold=1, primary="#FFFFFF", active="#00E5FF", outline="#0077FF", ow=6,
                 shadow=0, box=False, upper=True, pop=True, mode="phrase", mv=520, scale_active=0, glow=1),
    "boxed": dict(font="Arial", size=76, bold=1, primary="#FFFFFF", active="#FFD400", outline="#000000", ow=14,
                  shadow=0, box=True, upper=False, pop=False, mode="phrase", mv=470, scale_active=0, glow=0),
    "one_word": dict(font="Arial", size=150, bold=1, primary="#FFFFFF", active="#FFE600", outline="#000000", ow=10,
                     shadow=3, box=False, upper=True, pop=True, mode="word", mv=650, scale_active=0, glow=0),
    "minimal": dict(font="Arial", size=62, bold=0, primary="#FFFFFF", active="#FFFFFF", outline="#000000", ow=4,
                    shadow=1, box=False, upper=False, pop=False, mode="phrase", mv=300, scale_active=0, glow=0),
}


def build_cues(words, max_words=3, max_chars=22, gap=0.35):
    """Group words into short cues. words: [{'w','start','end'}] on the clip timeline."""
    groups, cur = [], []
    for w in words:
        if cur:
            chars = sum(len(x["w"]) + 1 for x in cur) + len(w["w"])
            if (len(cur) >= max_words or chars > max_chars or w["start"] - cur[-1]["end"] > gap
                    or cur[-1]["w"].endswith(SENT + (",",))):
                groups.append(cur)
                cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    cues = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1][0]["start"] if i + 1 < len(groups) else 1e9
        prev_end = cues[-1]["end"] if cues else 0.0
        start = max(g[0]["start"] - 0.03, prev_end)
        end = min(g[-1]["end"] + 0.12, nxt)
        end = max(end, min(start + 0.35, nxt))          # min on-screen time
        end = min(end, max(start + 2.0, g[-1]["end"]))  # max on-screen time
        cues.append({"start": start, "end": end, "words": g})
    return cues


def _ts(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _esc(s):
    return s.replace("{", "(").replace("}", ")").replace("\\", "")


def to_ass(cues, template="yellow_pop", width=1080, height=1920):
    t = TEMPLATES.get(template) or TEMPLATES["yellow_pop"]
    style_box = 3 if t["box"] else 1
    back = _bgr("#000000", 90 if t["box"] else 128)
    outc = _bgr(t["outline"], 90) if t["box"] else _bgr(t["outline"])
    head = (
        "[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
        f"PlayResX: {width}\nPlayResY: {height}\n\n[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,"
        "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,"
        "MarginR,MarginV,Encoding\n"
        f"Style: Main,{t['font']},{t['size']},{_bgr(t['primary'])},{_bgr(t['primary'])},{outc},{back},"
        f"{-1 if t['bold'] else 0},0,0,0,100,100,0,0,{style_box},{t['ow']},{t['shadow']},2,60,60,{t['mv']},1\n\n"
        "[Events]\nFormat: Layer,Start,End,Name,Style,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    pop = r"{\fscx82\fscy82\t(0,90,\fscx100\fscy100)}" if t["pop"] else ""
    glow = r"{\blur5}" if t["glow"] else ""
    sa = t["scale_active"]
    lines = []
    for cue in cues:
        ws = [(_esc(w["w"]).upper() if t["upper"] else _esc(w["w"])) for w in cue["words"]]
        for i, w in enumerate(cue["words"]):
            s = cue["start"] if i == 0 else w["start"]
            e = cue["words"][i + 1]["start"] if i + 1 < len(ws) else cue["end"]
            if t["mode"] == "word":
                body = ws[i]
            else:
                parts = []
                for j, txt in enumerate(ws):
                    on = j == i
                    tag = f"\\c{_bgr(t['active'] if on else t['primary'])}"
                    if sa:
                        tag += f"\\fscx{sa if on else 100}\\fscy{sa if on else 100}"
                    parts.append(f"{{{tag}}}{txt}")
                body = " ".join(parts)
            lines.append(f"Dialogue: 0,{_ts(s)},{_ts(e)},,Main,0,0,0,,{glow}{pop if (i == 0 or t['mode'] == 'word') else ''}{body}")
    return head + "\n".join(lines) + "\n"
