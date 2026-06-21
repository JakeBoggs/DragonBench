#!/usr/bin/env python3
"""Build focused image examples for AnoleGeneParse intron comparisons."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from build_intron_text_comparison_report import (
    COLORS,
    FONT_BODY,
    FONT_H2,
    FONT_MONO,
    FONT_MONO_SMALL,
    FONT_SMALL,
    FONT_TITLE,
    RESULTS_DIR,
    clean_slug,
    interval_covers,
    raw_interval_text,
    select_comparisons,
)


OUT_DIR = RESULTS_DIR / "intron_focus_examples"


def overlaps(a: dict[str, int], b: dict[str, int]) -> bool:
    return max(a["start"], b["start"]) < min(a["end"], b["end"])


def clamp_window(center: int, sequence_length: int, radius: int = 54) -> tuple[int, int]:
    start = max(0, center - radius)
    end = min(sequence_length, center + radius)
    if end - start < radius * 2:
        if start == 0:
            end = min(sequence_length, radius * 2)
        elif end == sequence_length:
            start = max(0, sequence_length - radius * 2)
    return start, end


def closest_boundary_distance(point: int, intervals: list[dict[str, int]]) -> int:
    if not intervals:
        return 10**9
    boundaries = [value for item in intervals for value in (item["start"], item["end"])]
    return min(abs(point - boundary) for boundary in boundaries)


def focus_point(comp) -> tuple[int, str]:
    if not comp.bad_introns:
        point = comp.truth[0]["start"]
        if len(comp.truth) > 1:
            point = comp.truth[1]["start"]
        return point, "weak model returned no valid intron spans here"

    if any(item["start"] <= 5 and item["end"] >= len(comp.sequence) - 5 for item in comp.bad_introns):
        return comp.truth[0]["start"], "weak model over-removed nearly the whole sequence"

    false_positive = [
        item
        for item in comp.bad_introns
        if not any(overlaps(item, truth) for truth in comp.truth)
    ]
    if false_positive:
        item = false_positive[0]
        return (item["start"] + item["end"]) // 2, "weak model predicts an intron where truth has exon sequence"

    boundary_candidates = []
    for item in comp.truth:
        for point in (item["start"], item["end"]):
            boundary_candidates.append((closest_boundary_distance(point, comp.good_introns), point))
    boundary_candidates.sort(reverse=True)
    if boundary_candidates:
        return boundary_candidates[0][1], "strong model is close but shifted at this boundary"

    return comp.truth[0]["start"], "focused boundary view"


def compressed_windows(comp, max_chars_per_line: int = 126, max_lines: int = 2) -> list[tuple[int, int]]:
    sequence_length = len(comp.sequence)
    points = []
    for intervals in [comp.truth, comp.good_introns, comp.bad_introns]:
        for item in intervals:
            points.extend([item["start"], item["end"]])

    if not points:
        points = [sequence_length // 2]

    for radius in [10, 7, 5, 3]:
        windows = []
        for point in sorted(set(points)):
            windows.append((max(0, point - radius), min(sequence_length, point + radius)))
        merged: list[tuple[int, int]] = []
        for start, end in windows:
            if not merged or start > merged[-1][1] + 6:
                merged.append((start, end))
            else:
                old_start, old_end = merged[-1]
                merged[-1] = (old_start, max(old_end, end))
        if compressed_token_count(merged, sequence_length) <= max_chars_per_line * max_lines:
            return merged
    return merged


def compressed_token_count(windows: list[tuple[int, int]], sequence_length: int) -> int:
    total = 0
    cursor = 0
    for start, end in windows:
        total += end - start
        cursor = end
    return total


def compressed_tokens(sequence: str, windows: list[tuple[int, int]]) -> list[tuple[str, int | None]]:
    tokens: list[tuple[str, int | None]] = []
    cursor = 0
    for start, end in windows:
        for position in range(start, end):
            tokens.append((sequence[position], position))
        cursor = end
    return tokens


def wrap_tokens(tokens: list[tuple[str, int | None]], max_chars: int = 126) -> list[list[tuple[str, int | None]]]:
    lines = []
    current = []
    for token in tokens:
        current.append(token)
        if len(current) >= max_chars:
            lines.append(current)
            current = []
    if current:
        lines.append(current)
    return lines


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill=None) -> None:
    draw.text(xy, text, font=font, fill=fill or COLORS["text"])


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(box, radius=10, fill=COLORS["panel"], outline=COLORS["border"], width=1)


def interval_label(intervals: list[dict[str, int]], max_chars: int = 96) -> str:
    text = raw_interval_text(intervals)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def draw_track(draw, label: str, intervals, seq_len: int, x: int, y: int, width: int, stroke, fill) -> None:
    draw_text(draw, (x, y - 7), label, FONT_SMALL, COLORS["muted"])
    tx = x + 150
    draw.rounded_rectangle((tx, y, tx + width, y + 16), radius=7, fill=COLORS["exon"], outline=COLORS["border"])
    for item in intervals:
        left = tx + int(width * item["start"] / seq_len)
        right = tx + max(2, int(width * item["end"] / seq_len))
        draw.rounded_rectangle((left, y - 2, right, y + 18), radius=5, fill=fill, outline=stroke, width=2)
    draw_text(draw, (tx + width + 12, y - 7), f"n={len(intervals)}", FONT_SMALL, COLORS["muted"])


def draw_zoom_sequence(draw, comp, window: tuple[int, int], x: int, y: int, width: int) -> int:
    start, end = window
    seq = comp.sequence[start:end]
    char_w = 13
    line_len = min(len(seq), (width - 150) // char_w)
    shown = seq[:line_len]
    base_x = x + 92

    rounded_panel(draw, (x, y, x + width, y + 164))
    draw_text(draw, (x + 18, y + 14), f"Focused DNA window {start}-{start + len(shown)}", FONT_H2)
    draw_text(draw, (x + 18, y + 50), "Green background = true intron bases. Bars below show T/S/W coverage.", FONT_SMALL, COLORS["muted"])

    yy = y + 84
    draw_text(draw, (x + 24, yy), f"{start:>5}", FONT_MONO_SMALL, COLORS["muted"])
    for offset, base in enumerate(shown):
        pos = start + offset
        bx = base_x + offset * char_w
        if interval_covers(comp.truth, pos):
            draw.rectangle((bx - 1, yy - 2, bx + char_w - 1, yy + 22), fill=COLORS["truth_fill"])
        draw_text(draw, (bx, yy), base, FONT_MONO, COLORS["text"])

    rows = [
        ("T", comp.truth, COLORS["truth"]),
        ("S", comp.good_introns, COLORS["good"]),
        ("W", comp.bad_introns, COLORS["bad"]),
    ]
    for row_index, (label, intervals, color) in enumerate(rows):
        ty = yy + 34 + row_index * 17
        draw_text(draw, (x + 62, ty - 7), label, FONT_MONO_SMALL, color)
        for offset in range(len(shown)):
            pos = start + offset
            bx = base_x + offset * char_w
            if interval_covers(intervals, pos):
                draw.rectangle((bx, ty, bx + char_w - 4, ty + 10), fill=color)
    return y + 184


def render_focus_card(comp, output_path: Path) -> str:
    width = 1600
    height = 320
    margin = 46
    _, focus_reason = focus_point(comp)
    image = Image.new("RGB", (width, height), COLORS["bg"])
    draw = ImageDraw.Draw(image)

    y = 34
    draw_text(draw, (margin, y), f"{comp.question_id}: intron coordinate context", FONT_TITLE)
    y += 44
    draw_text(
        draw,
        (margin, y),
        f"{comp.good_model} {comp.good_reward:.3f} vs {comp.bad_model} {comp.bad_reward:.3f}; gap {comp.delta:.3f}; sequence length {len(comp.sequence):,} bp",
        FONT_BODY,
        COLORS["muted"],
    )

    y += 62
    track_width = width - 2 * margin - 300
    draw_track(draw, "Truth", comp.truth, len(comp.sequence), margin, y, track_width, COLORS["truth"], COLORS["truth_fill"])
    draw_track(draw, comp.good_model, comp.good_introns, len(comp.sequence), margin, y + 52, track_width, COLORS["good"], COLORS["good_fill"])
    draw_track(draw, comp.bad_model, comp.bad_introns, len(comp.sequence), margin, y + 104, track_width, COLORS["bad"], COLORS["bad_fill"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return focus_reason


def markdown(comparisons, rows) -> str:
    lines = [
        "# Focused Intron Examples",
        "",
        "Small AnoleGeneParse examples built for slide review. Each image shows the whole-sequence coordinate context.",
        "",
        "Rows show ground-truth intron spans, stronger model spans, and weaker model spans across the same sequence.",
        "",
        "## Examples",
        "",
        "| Example | Task | Focus | Strong | Reward | Weak | Reward | Image |",
        "|---:|---|---|---|---:|---|---:|---|",
    ]
    for idx, row in enumerate(rows, start=1):
        comp = comparisons[idx - 1]
        lines.append(
            f"| {idx} | {comp.question_id} | {row['focus']} | {comp.good_model} | "
            f"{comp.good_reward:.3f} | {comp.bad_model} | {comp.bad_reward:.3f} | "
            f"[{Path(row['image']).name}]({row['image']}) |"
        )

    for idx, row in enumerate(rows, start=1):
        comp = comparisons[idx - 1]
        lines.extend(
            [
                "",
                f"## {idx}. {comp.question_id}: {row['focus']}",
                "",
                f"Caption: truth `{raw_interval_text(comp.truth)}`; {comp.good_model} predicts "
                f"`{raw_interval_text(comp.good_introns)}`; {comp.bad_model} predicts "
                f"`{raw_interval_text(comp.bad_introns)}`.",
                "",
                f"![{comp.question_id} focused intron example]({row['image']})",
            ]
        )

    lines.extend(
        [
            "",
            "## Source Data",
            "",
            "- Current row dataset: [current_full_run_traces.csv](data/current_full_run_traces.csv)",
            "- Image index: [intron_focus_examples_index.csv](intron_focus_examples/intron_focus_examples_index.csv)",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    comparisons = select_comparisons(limit=5)
    rows = []
    for comp in comparisons:
        slug = f"{comp.question_id}_{clean_slug(comp.good_model)}_vs_{clean_slug(comp.bad_model)}"
        image_rel = f"intron_focus_examples/{slug}.png"
        focus = render_focus_card(comp, RESULTS_DIR / image_rel)
        rows.append(
            {
                "task_id": comp.question_id,
                "focus": focus,
                "good_model": comp.good_model,
                "good_reward": f"{comp.good_reward:.6f}",
                "bad_model": comp.bad_model,
                "bad_reward": f"{comp.bad_reward:.6f}",
                "truth_introns": json.dumps(comp.truth, separators=(",", ":")),
                "good_introns": json.dumps(comp.good_introns, separators=(",", ":")),
                "bad_introns": json.dumps(comp.bad_introns, separators=(",", ":")),
                "image": image_rel,
            }
        )

    with (OUT_DIR / "intron_focus_examples_index.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (RESULTS_DIR / "INTRON_INTERESTING_COMPARISONS.md").write_text(
        markdown(comparisons, rows)
    )
    print(f"Wrote {len(rows)} focused intron examples to {OUT_DIR}")


if __name__ == "__main__":
    main()
