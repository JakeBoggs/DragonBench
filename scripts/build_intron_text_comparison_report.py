#!/usr/bin/env python3
"""Build image-backed intron solution comparison report."""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "reports/dragonbench_results_2026-06-21"
TRACES_CSV = RESULTS_DIR / "data/current_full_run_traces.csv"
EVAL_JSONL = ROOT / "data/eval/dragonbench_eval_v0.scoreable.jsonl"
OUT_DIR = RESULTS_DIR / "intron_text_comparisons"
TRACE_DIRS = [
    ROOT / "reports/modal_full_run/trace_events",
    ROOT / "reports/latest_eval_updates/trace_cache",
]


COLORS = {
    "bg": (248, 250, 252),
    "panel": (255, 255, 255),
    "border": (203, 213, 225),
    "text": (15, 23, 42),
    "muted": (71, 85, 105),
    "truth": (22, 163, 74),
    "truth_fill": (187, 247, 208),
    "good": (37, 99, 235),
    "good_fill": (191, 219, 254),
    "bad": (220, 38, 38),
    "bad_fill": (254, 202, 202),
    "exon": (226, 232, 240),
}


@dataclass
class Comparison:
    question_id: str
    sequence: str
    truth: list[dict[str, int]]
    good_model: str
    good_reward: float
    good_trace: str
    good_introns: list[dict[str, int]]
    bad_model: str
    bad_reward: float
    bad_trace: str
    bad_introns: list[dict[str, int]]

    @property
    def delta(self) -> float:
        return self.good_reward - self.bad_reward


def load_font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            "/System/Library/Fonts/Menlo.ttc",
            "/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/SFNSMono.ttf",
        ]
        if mono
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = load_font(34)
FONT_H2 = load_font(24)
FONT_BODY = load_font(20)
FONT_SMALL = load_font(16)
FONT_MONO = load_font(18, mono=True)
FONT_MONO_SMALL = load_font(15, mono=True)


def clean_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def read_eval_cards() -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    with EVAL_JSONL.open() as handle:
        for line in handle:
            card = json.loads(line)
            if card.get("task") == "AnoleGeneParse":
                cards[card["id"]] = card
    return cards


def read_trace_rows() -> list[dict[str, str]]:
    with TRACES_CSV.open() as handle:
        rows = list(csv.DictReader(handle))
    return [
        row
        for row in rows
        if row.get("task") == "AnoleGeneParse" and row.get("status") == "completed"
    ]


def trace_path(trace_id: str) -> Path | None:
    for directory in TRACE_DIRS:
        path = directory / f"{trace_id}.json"
        if path.exists():
            return path
    return None


def extract_answer(trace_id: str) -> dict[str, Any] | None:
    path = trace_path(trace_id)
    if path is None:
        return None
    payload = json.loads(path.read_text())
    events = payload if isinstance(payload, list) else payload.get("events", [])
    for event in events:
        if not isinstance(event, dict):
            continue
        args = event.get("arguments")
        if isinstance(args, dict) and "answer_json" in args:
            return parse_answer_json(args["answer_json"])
        for tool_call in event.get("tool_calls", []):
            args = tool_call.get("arguments", {})
            if "answer_json" in args:
                return parse_answer_json(args["answer_json"])
    return None


def parse_answer_json(answer_json: Any) -> dict[str, Any] | None:
    if isinstance(answer_json, dict):
        return answer_json
    if not isinstance(answer_json, str):
        return None
    try:
        parsed = json.loads(answer_json)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def normalized_intervals(items: Any, sequence_length: int) -> list[dict[str, int]]:
    if not isinstance(items, list):
        return []
    intervals: list[dict[str, int]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            start = int(item["start"])
            end = int(item["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= start < end <= sequence_length:
            intervals.append({"start": start, "end": end})
    return sorted(intervals, key=lambda item: (item["start"], item["end"]))


def raw_interval_text(items: list[dict[str, int]]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(f"{item['start']}-{item['end']}" for item in items) + "]"


def select_comparisons(limit: int = 5) -> list[Comparison]:
    cards = read_eval_cards()
    rows = read_trace_rows()
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["question_id"], []).append(row)

    comparisons: list[Comparison] = []
    for question_id, group in grouped.items():
        card = cards.get(question_id)
        if not card:
            continue
        sequence = card["question"]["model_input"]["sequence"]
        truth = normalized_intervals(
            card["hidden_answer"]["answer"]["introns"],
            len(sequence),
        )
        sorted_rows = sorted(group, key=lambda row: float(row["reward"]), reverse=True)
        good = sorted_rows[0]
        bad = sorted_rows[-1]
        good_answer = extract_answer(good["trace_id"])
        bad_answer = extract_answer(bad["trace_id"])
        if not good_answer or not bad_answer:
            continue
        comparison = Comparison(
            question_id=question_id,
            sequence=sequence,
            truth=truth,
            good_model=good["model_label"],
            good_reward=float(good["reward"]),
            good_trace=good["trace_id"],
            good_introns=normalized_intervals(good_answer.get("introns"), len(sequence)),
            bad_model=bad["model_label"],
            bad_reward=float(bad["reward"]),
            bad_trace=bad["trace_id"],
            bad_introns=normalized_intervals(bad_answer.get("introns"), len(sequence)),
        )
        if comparison.delta >= 0.3:
            comparisons.append(comparison)

    comparisons.sort(key=lambda item: (item.delta, item.good_reward), reverse=True)
    return diverse_comparisons(comparisons, limit=limit)


def intervals_equal(left: list[dict[str, int]], right: list[dict[str, int]]) -> bool:
    return raw_interval_text(left) == raw_interval_text(right)


def mostly_full_sequence(comp: Comparison) -> bool:
    return any(
        item["start"] <= 5 and item["end"] >= len(comp.sequence) - 5
        for item in comp.bad_introns
    )


def diverse_comparisons(comparisons: list[Comparison], limit: int) -> list[Comparison]:
    """Pick a presentation set with different failure modes."""
    selected: list[Comparison] = []

    def add_first(predicate) -> None:
        if len(selected) >= limit:
            return
        for comp in comparisons:
            if comp.question_id in {item.question_id for item in selected}:
                continue
            if predicate(comp):
                selected.append(comp)
                return

    add_first(
        lambda comp: intervals_equal(comp.good_introns, comp.truth)
        and not comp.bad_introns
        and len(comp.truth) == 1
    )
    add_first(
        lambda comp: intervals_equal(comp.good_introns, comp.truth)
        and not comp.bad_introns
        and len(comp.truth) >= 3
    )
    add_first(
        lambda comp: 0.85 <= comp.good_reward < 1.0
        and not comp.bad_introns
        and len(comp.truth) >= 2
    )
    add_first(
        lambda comp: mostly_full_sequence(comp)
        and comp.good_reward >= 0.75
    )
    add_first(
        lambda comp: len(comp.bad_introns) >= 3
        and comp.bad_reward > 0
        and comp.good_reward >= 0.75
    )

    for comp in comparisons:
        if len(selected) >= limit:
            break
        if comp.question_id not in {item.question_id for item in selected}:
            selected.append(comp)
    return selected[:limit]


def interval_covers(intervals: list[dict[str, int]], position: int) -> bool:
    return any(item["start"] <= position < item["end"] for item in intervals)


def boundary_windows(comp: Comparison, flank: int = 45, max_windows: int = 7) -> list[tuple[int, int]]:
    points: list[int] = []
    for intervals in [comp.truth, comp.good_introns, comp.bad_introns]:
        for item in intervals:
            points.extend([item["start"], item["end"]])
    merged: list[tuple[int, int]] = []
    for point in sorted(set(points)):
        start = max(0, point - flank)
        end = min(len(comp.sequence), point + flank)
        if not merged or start > merged[-1][1] + 12:
            merged.append((start, end))
        else:
            old_start, old_end = merged[-1]
            merged[-1] = (old_start, max(old_end, end))
    merged.sort(key=lambda span: span[1] - span[0], reverse=True)
    selected = sorted(merged[:max_windows])
    return selected


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill=None) -> None:
    draw.text(xy, text, font=font, fill=fill or COLORS["text"])


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(box, radius=10, fill=COLORS["panel"], outline=COLORS["border"], width=1)


def draw_legend(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    items = [
        ("Truth intron", COLORS["truth_fill"], COLORS["truth"]),
        ("Strong model", COLORS["good_fill"], COLORS["good"]),
        ("Weak model", COLORS["bad_fill"], COLORS["bad"]),
    ]
    cursor = x
    for label, fill, stroke in items:
        draw.rounded_rectangle((cursor, y, cursor + 34, y + 18), radius=5, fill=fill, outline=stroke, width=2)
        draw_text(draw, (cursor + 44, y - 2), label, FONT_SMALL, COLORS["muted"])
        cursor += 190


def draw_track(
    draw: ImageDraw.ImageDraw,
    label: str,
    intervals: list[dict[str, int]],
    sequence_length: int,
    x: int,
    y: int,
    width: int,
    color: tuple[int, int, int],
    fill: tuple[int, int, int],
) -> None:
    draw_text(draw, (x, y - 8), label, FONT_SMALL, COLORS["muted"])
    track_x = x + 170
    track_y = y
    track_h = 18
    draw.rounded_rectangle(
        (track_x, track_y, track_x + width, track_y + track_h),
        radius=7,
        fill=COLORS["exon"],
        outline=COLORS["border"],
    )
    for item in intervals:
        left = track_x + int(width * item["start"] / sequence_length)
        right = track_x + max(2, int(width * item["end"] / sequence_length))
        draw.rounded_rectangle((left, track_y - 2, right, track_y + track_h + 2), radius=5, fill=fill, outline=color, width=2)
    draw_text(draw, (track_x + width + 14, y - 8), f"n={len(intervals)}", FONT_SMALL, COLORS["muted"])


def draw_coordinate_summary(draw: ImageDraw.ImageDraw, comp: Comparison, x: int, y: int, width: int) -> int:
    rounded_panel(draw, (x, y, x + width, y + 188))
    draw_text(draw, (x + 22, y + 18), "Coordinate tracks", FONT_H2)
    draw_legend(draw, x + 310, y + 23)
    track_width = width - 300
    draw_track(draw, "Ground truth", comp.truth, len(comp.sequence), x + 22, y + 74, track_width, COLORS["truth"], COLORS["truth_fill"])
    draw_track(draw, comp.good_model, comp.good_introns, len(comp.sequence), x + 22, y + 112, track_width, COLORS["good"], COLORS["good_fill"])
    draw_track(draw, comp.bad_model, comp.bad_introns, len(comp.sequence), x + 22, y + 150, track_width, COLORS["bad"], COLORS["bad_fill"])
    return y + 210


def draw_solution_text(draw: ImageDraw.ImageDraw, comp: Comparison, x: int, y: int, width: int) -> int:
    rounded_panel(draw, (x, y, x + width, y + 148))
    draw_text(draw, (x + 22, y + 18), "Submitted coordinate text", FONT_H2)
    rows = [
        ("Truth", raw_interval_text(comp.truth), COLORS["truth"]),
        (f"{comp.good_model} ({comp.good_reward:.3f})", raw_interval_text(comp.good_introns), COLORS["good"]),
        (f"{comp.bad_model} ({comp.bad_reward:.3f})", raw_interval_text(comp.bad_introns), COLORS["bad"]),
    ]
    yy = y + 58
    for label, text, color in rows:
        draw.rounded_rectangle((x + 22, yy + 3, x + 42, yy + 23), radius=5, fill=color)
        draw_text(draw, (x + 54, yy), label, FONT_SMALL, COLORS["muted"])
        draw_text(draw, (x + 310, yy), text[:130], FONT_MONO_SMALL)
        yy += 28
    return y + 170


def draw_sequence_window(
    draw: ImageDraw.ImageDraw,
    comp: Comparison,
    window: tuple[int, int],
    x: int,
    y: int,
    width: int,
) -> int:
    start, end = window
    seq = comp.sequence[start:end]
    char_w = 15
    line_len = min(86, max(50, (width - 160) // char_w))
    lines = [seq[i : i + line_len] for i in range(0, len(seq), line_len)]
    line_h = 82
    height = 40 + len(lines) * line_h
    rounded_panel(draw, (x, y, x + width, y + height))
    draw_text(draw, (x + 18, y + 12), f"Sequence window {start}-{end}", FONT_SMALL, COLORS["muted"])

    yy = y + 40
    for line_index, line in enumerate(lines):
        line_start = start + line_index * line_len
        draw_text(draw, (x + 18, yy), f"{line_start:>5}", FONT_MONO_SMALL, COLORS["muted"])
        base_x = x + 84
        for offset, base in enumerate(line):
            pos = line_start + offset
            bx = base_x + offset * char_w
            if interval_covers(comp.truth, pos):
                draw.rectangle((bx - 1, yy - 2, bx + char_w - 1, yy + 22), fill=COLORS["truth_fill"])
            draw_text(draw, (bx, yy), base, FONT_MONO, COLORS["text"])

        tracks = [
            ("T", comp.truth, COLORS["truth"]),
            ("S", comp.good_introns, COLORS["good"]),
            ("W", comp.bad_introns, COLORS["bad"]),
        ]
        for track_index, (label, intervals, color) in enumerate(tracks):
            ty = yy + 29 + track_index * 14
            draw_text(draw, (x + 56, ty - 5), label, FONT_MONO_SMALL, color)
            for offset in range(len(line)):
                pos = line_start + offset
                bx = base_x + offset * char_w
                if interval_covers(intervals, pos):
                    draw.rectangle((bx, ty, bx + char_w - 3, ty + 8), fill=color)
        yy += line_h
    return y + height + 16


def render_comparison(comp: Comparison, output_path: Path) -> None:
    width = 1800
    windows = boundary_windows(comp)
    estimated_height = 430 + sum(70 + math.ceil((end - start) / 86) * 82 for start, end in windows)
    height = max(1050, min(2600, estimated_height))
    image = Image.new("RGB", (width, height), COLORS["bg"])
    draw = ImageDraw.Draw(image)

    margin = 54
    y = 42
    draw_text(draw, (margin, y), f"{comp.question_id}: intron span comparison", FONT_TITLE)
    y += 48
    caption = (
        f"{comp.good_model} {comp.good_reward:.3f} vs "
        f"{comp.bad_model} {comp.bad_reward:.3f}; gap {comp.delta:.3f}; "
        f"sequence length {len(comp.sequence):,} bp"
    )
    draw_text(draw, (margin, y), caption, FONT_BODY, COLORS["muted"])
    y += 46
    y = draw_coordinate_summary(draw, comp, margin, y, width - 2 * margin)
    y = draw_solution_text(draw, comp, margin, y, width - 2 * margin)

    draw_text(draw, (margin, y), "Boundary-level DNA text highlights", FONT_H2)
    draw_text(draw, (margin + 430, y + 5), "T = truth, S = strong model, W = weak model", FONT_SMALL, COLORS["muted"])
    y += 38
    for window in windows:
        if y > height - 180:
            break
        y = draw_sequence_window(draw, comp, window, margin, y, width - 2 * margin)

    image.crop((0, 0, width, min(height, y + 28))).save(output_path)


def markdown(comparisons: list[Comparison], image_rows: list[dict[str, str]]) -> str:
    lines = [
        "# Interesting Intron Text Comparisons",
        "",
        "High-contrast AnoleGeneParse examples. Each PNG embeds the model coordinate text and sequence-level highlights.",
        "",
        "Legend in each image: `T` = ground truth intron coverage, `S` = stronger model prediction, `W` = weaker model prediction.",
        "",
        "## Best Presentation Picks",
        "",
        "| Rank | Task | Strong solution | Reward | Weak solution | Reward | Gap | Image |",
        "|---:|---|---|---:|---|---:|---:|---|",
    ]
    for index, row in enumerate(image_rows, start=1):
        comp = comparisons[index - 1]
        lines.append(
            f"| {index} | {comp.question_id} | {comp.good_model} | {comp.good_reward:.3f} | "
            f"{comp.bad_model} | {comp.bad_reward:.3f} | {comp.delta:.3f} | "
            f"[{Path(row['image']).name}]({row['image']}) |"
        )

    for index, row in enumerate(image_rows, start=1):
        comp = comparisons[index - 1]
        lines.extend(
            [
                "",
                f"## {index}. {comp.question_id}: {comp.good_model} vs {comp.bad_model}",
                "",
                f"Caption: {comp.good_model} predicts {raw_interval_text(comp.good_introns)} "
                f"against truth {raw_interval_text(comp.truth)}; {comp.bad_model} predicts "
                f"{raw_interval_text(comp.bad_introns)}. Reward gap: `{comp.delta:.3f}`.",
                "",
                f"![{comp.question_id} intron comparison]({row['image']})",
            ]
        )

    lines.extend(
        [
            "",
            "## Source Data",
            "",
            "- Current row dataset: [current_full_run_traces.csv](data/current_full_run_traces.csv)",
            "- Eval questions: `data/eval/dragonbench_eval_v0.scoreable.jsonl`",
            "- Image index: [intron_text_comparison_index.csv](intron_text_comparisons/intron_text_comparison_index.csv)",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    comparisons = select_comparisons(limit=5)
    image_rows: list[dict[str, str]] = []
    for comp in comparisons:
        slug = f"{comp.question_id}_{clean_slug(comp.good_model)}_vs_{clean_slug(comp.bad_model)}"
        image_rel = f"intron_text_comparisons/{slug}.png"
        render_comparison(comp, RESULTS_DIR / image_rel)
        image_rows.append(
            {
                "task_id": comp.question_id,
                "good_model": comp.good_model,
                "good_reward": f"{comp.good_reward:.6f}",
                "bad_model": comp.bad_model,
                "bad_reward": f"{comp.bad_reward:.6f}",
                "delta": f"{comp.delta:.6f}",
                "truth_introns": json.dumps(comp.truth, separators=(",", ":")),
                "good_introns": json.dumps(comp.good_introns, separators=(",", ":")),
                "bad_introns": json.dumps(comp.bad_introns, separators=(",", ":")),
                "image": image_rel,
            }
        )

    index_path = OUT_DIR / "intron_text_comparison_index.csv"
    with index_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(image_rows[0].keys()))
        writer.writeheader()
        writer.writerows(image_rows)

    (RESULTS_DIR / "INTRON_INTERESTING_COMPARISONS.md").write_text(
        markdown(comparisons, image_rows)
    )
    print(f"Wrote {len(image_rows)} intron comparison images to {OUT_DIR}")


if __name__ == "__main__":
    main()
