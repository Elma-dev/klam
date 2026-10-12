"""ASS (Advanced SubStation Alpha) generation from the shared style model.

Coordinates are expressed in output pixels (PlayResX/Y = target resolution).
``CaptionStyle`` lengths (font size, margins, outline, padding, shadow) are
defined at :data:`reference_height` (1080 px) and scaled by ``height/1080`` so
the preview and the burned-in export match.
"""

from __future__ import annotations

import re

from ..schema import Alignment, CaptionStyle, Project, Segment, VerticalPosition

_VMAP = {
    VerticalPosition.bottom: 0,
    VerticalPosition.middle: 3,
    VerticalPosition.top: 6,
}
_HMAP = {Alignment.left: 1, Alignment.center: 2, Alignment.right: 3}

HEADER_FORMAT = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
    "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
    "MarginL, MarginR, MarginV, Encoding"
)
EVENT_FORMAT = (
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
)


def ass_color(hex_color: str, opacity: float = 1.0) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    h = h.ljust(6, "0")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    alpha = round((1.0 - max(0.0, min(1.0, opacity))) * 255)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def ass_time(seconds: float) -> str:
    centis = round(max(0.0, seconds) * 100)
    hours, rem = divmod(centis, 360000)
    minutes, rem = divmod(rem, 6000)
    secs, cs = divmod(rem, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _alignment(style: CaptionStyle) -> int:
    return _VMAP[style.position.vertical] + _HMAP[style.align]


def _style_line(style: CaptionStyle, width: int, height: int, reference: int) -> str:
    k = height / reference
    boxed = style.background.opacity > 0.001
    if boxed:
        border_style = 3
        outline = style.background.padding * k
        shadow = 0.0
        outline_colour = ass_color(style.background.color, 1.0)
        back_colour = ass_color(style.background.color, style.background.opacity)
    else:
        border_style = 1
        outline = style.outline.width * k
        shadow = max(abs(style.shadow.offset_x), abs(style.shadow.offset_y)) * k
        outline_colour = ass_color(style.outline.color, 1.0)
        back_colour = ass_color(style.shadow.color, style.shadow.opacity)

    # ASS only carries a binary bold flag, so the preview's 600 renders as 400
    # unless we treat semibold-and-up as bold. Threshold matches the preview.
    bold = -1 if style.font_weight >= 600 else 0
    italic = -1 if style.italic else 0
    primary = ass_color(style.color, 1.0)
    secondary = ass_color(style.active_word.color, 1.0)
    margin = style.margin_h * k
    margin_v = style.margin_v * k
    return (
        f"Style: Default,{style.font_family},{style.font_size * k:.1f},"
        f"{primary},{secondary},{outline_colour},{back_colour},"
        f"{bold},{italic},0,0,100,100,0,0,{border_style},{outline:.1f},{shadow:.1f},"
        f"{_alignment(style)},{margin:.0f},{margin:.0f},{margin_v:.0f},1"
    )


def _segment_text(segment: Segment) -> str:
    text = segment.text.replace("\n", "\\N")
    text = text.replace("{", "\\{").replace("}", "\\}")
    if segment.dir == "rtl":
        text = "\u200f" + text
    elif segment.dir == "ltr":
        text = "\u200e" + text
    return text


def _escape(text: str, dir_override: str | None = None) -> str:
    escaped = text.replace("\n", "\\N").replace("{", "\\{").replace("}", "\\}")
    if dir_override == "rtl":
        return "\u200f" + escaped
    elif dir_override == "ltr":
        return "\u200e" + escaped
    return escaped


def _line_starts(text: str) -> set[int]:
    """Word indices that begin a new line, taken from the segment's own text.

    The word-by-word modes rebuild the caption from `segment.words`, which loses
    the newlines the editor produced. This recovers them so the export keeps the
    creator's line breaks instead of letting libass re-wrap the text.
    """
    starts: set[int] = set()
    seen = 0
    for index, line in enumerate(text.split("\n")):
        if index > 0:
            starts.add(seen)
        seen += len(line.split())
    return starts


def _join_words(parts: list[str], line_starts: set[int]) -> str:
    """Join rebuilt words, breaking where the original text broke."""
    out: list[str] = []
    for index, part in enumerate(parts):
        if index:
            out.append("\\N" if index in line_starts else " ")
        out.append(part)
    return "".join(out)


_RTL_CHARS = re.compile(
    "[֐-׿؀-ۿ܀-ݏݐ-ݿ"
    "ࢠ-ࣿיִ-﷿ﹰ-﻿]"
)
_LTR_CHARS = re.compile("[A-Za-zÀ-ɏ]")


def _segment_is_rtl(segment: Segment) -> bool:
    if segment.dir == "ltr":
        return False
    return bool(_RTL_CHARS.search(segment.text))


def _visual_order(
    words: list[str], line_starts: set[int], rtl: bool
) -> tuple[list[int], set[int]]:
    """Word indices in the order they must be *emitted*.

    libass lays override-split runs out in emission order, so a caption rebuilt
    from per-word colour overrides comes out with its words reversed unless we
    emit them in the order a reader sees them. Words that are Latin (French or
    English inside Darija speech) keep their own order and stay as one run.
    """
    if not rtl:
        return list(range(len(words))), set(line_starts)

    lines: list[list[int]] = []
    current: list[int] = []
    for index in range(len(words)):
        if index in line_starts and current:
            lines.append(current)
            current = []
        current.append(index)
    if current:
        lines.append(current)

    order: list[int] = []
    breaks: set[int] = set()
    for line_index, line in enumerate(lines):
        if line_index:
            breaks.add(len(order))
        runs: list[tuple[bool, list[int]]] = []
        for index in line:
            # Neutral tokens (digits, punctuation) ride with the RTL run.
            is_rtl = not _LTR_CHARS.search(words[index])
            if runs and runs[-1][0] == is_rtl:
                runs[-1][1].append(index)
            else:
                runs.append((is_rtl, [index]))
        for is_rtl, run in reversed(runs):
            order.extend(reversed(run) if is_rtl else run)
    return order, breaks


def _dialogue_lines(
    segment: Segment, style: CaptionStyle, width: int, height: int
) -> list[str]:
    prefix = ""
    if style.position.x is not None or style.position.y is not None:
        x = (style.position.x if style.position.x is not None else 0.5) * width
        y = (style.position.y if style.position.y is not None else 0.5) * height
        prefix = f"{{\\an5\\pos({x:.0f},{y:.0f})}}"

    mode = getattr(style.active_word, "mode", "highlight")
    words = segment.words

    # Word-by-word modes when words timestamps are available
    if words and len(words) > 0 and mode in ("reveal", "single", "highlight"):
        lines = []
        highlight_color = ass_color(style.active_word.color, 1.0)
        default_color = ass_color(style.color, 1.0)
        # Only trust the break map when the rebuilt words line up with the text.
        line_starts = (
            _line_starts(segment.text) if len(words) == len(segment.text.split()) else set()
        )
        rtl = _segment_is_rtl(segment)

        if mode == "single":
            # Show each word only during its spoken duration
            for w in words:
                word_text = _escape(w.word, segment.dir)
                body = f"{prefix}{{\\c{highlight_color}}}{word_text}"
                lines.append(
                    f"Dialogue: 0,{ass_time(w.start)},{ass_time(w.end)},"
                    f"Default,,0,0,0,,{body}"
                )
            return lines

        if mode == "reveal":
            # Word-by-word reveal: each word is added as it gets spoken
            for i, w in enumerate(words):
                end_time = words[i + 1].start if i + 1 < len(words) else segment.end
                revealed_words = []
                for j in range(i + 1):
                    wj = words[j]
                    text_j = _escape(wj.word, segment.dir)
                    if j == i:
                        revealed_words.append(
                            f"{{\\c{highlight_color}}}{text_j}{{\\c{default_color}}}"
                        )
                    else:
                        revealed_words.append(text_j)
                visible = i + 1
                order, out_breaks = _visual_order(
                    [word.word for word in words[:visible]],
                    {b for b in line_starts if b < visible},
                    rtl,
                )
                body = prefix + _join_words([revealed_words[k] for k in order], out_breaks)
                lines.append(
                    f"Dialogue: 0,{ass_time(w.start)},{ass_time(end_time)},"
                    f"Default,,0,0,0,,{body}"
                )
            return lines

        if mode == "highlight":
            # Karaoke highlight: all words visible, spoken word highlighted
            order, out_breaks = _visual_order(
                [word.word for word in words], line_starts, rtl
            )
            for i, w in enumerate(words):
                end_time = words[i + 1].start if i + 1 < len(words) else segment.end
                highlighted_words = []
                for j, wj in enumerate(words):
                    text_j = _escape(wj.word, segment.dir)
                    if j == i:
                        highlighted_words.append(
                            f"{{\\c{highlight_color}}}{text_j}{{\\c{default_color}}}"
                        )
                    else:
                        highlighted_words.append(text_j)
                body = prefix + _join_words([highlighted_words[k] for k in order], out_breaks)
                lines.append(
                    f"Dialogue: 0,{ass_time(w.start)},{ass_time(end_time)},"
                    f"Default,,0,0,0,,{body}"
                )
            return lines

    # Default fallback: entire segment shown throughout
    body = prefix + _escape(segment.text, segment.dir)
    return [
        f"Dialogue: 0,{ass_time(segment.start)},{ass_time(segment.end)},"
        f"Default,,0,0,0,,{body}"
    ]


def build_ass(
    project: Project,
    width: int,
    height: int,
    reference: int = 1080,
) -> str:
    style = project.style
    lines = [
        "[Script Info]",
        "; Generated by Vox Darija",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        HEADER_FORMAT,
        _style_line(style, width, height, reference),
        "",
        "[Events]",
        EVENT_FORMAT,
    ]
    for segment in project.segments:
        if segment.text.strip():
            lines.extend(_dialogue_lines(segment, style, width, height))
    return "\n".join(lines) + "\n"
