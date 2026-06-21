# Protein Fold Render Image Index

All paths are relative to this directory:
`reports/modal_full_run/protein_folds/high_contrast/images/render_only_labeled/`

The PNGs are intentionally unannotated. This index records what each filename shows.

## Counts

- Comparisons selected: `9`
- Individual per-comparison renders: `18` (`2` per comparison; duplicates are kept when the same model/task appears in multiple comparisons)
- Unique individual model/task renders in `individual_named/`: `17`
- Overlay-only renders: `9`
- Triptych renders: `9`

## Recommended Use

- Use `individual_by_comparison/` when you want every comparison to have two standalone model images.
- Use `individual_named/` when you want deduplicated standalone model/task images.
- Use `overlays/` for clean overlay-only renders.
- Use `triptychs/` for side-by-side good model, bad model, and overlay renders.

## Comparison Table

| Task | Good model | Good reward | Good render | Bad model | Bad reward | Bad render | Overlay | Triptych |
|---|---|---:|---|---|---:|---|---|---|
| DBEVAL-V0-056 | Opus 4.8 | 0.987 | [`DBEVAL-V0-056_opus48_reward0p987__comparison_opus48_vs_gpt5__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-056_opus48_reward0p987__comparison_opus48_vs_gpt5__good_vs_truth.png) | GPT-5 | 0.149 | [`DBEVAL-V0-056_gpt5_reward0p149__comparison_opus48_vs_gpt5__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-056_gpt5_reward0p149__comparison_opus48_vs_gpt5__bad_vs_truth.png) | [`opus48_vs_gpt5_DBEVAL-V0-056_overlay.png`](overlays/opus48_vs_gpt5_DBEVAL-V0-056_overlay.png) | [`opus48_vs_gpt5_DBEVAL-V0-056_triptych.png`](triptychs/opus48_vs_gpt5_DBEVAL-V0-056_triptych.png) |
| DBEVAL-V0-056 | Opus 4.8 | 0.987 | [`DBEVAL-V0-056_opus48_reward0p987__comparison_opus48_vs_gpt55__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-056_opus48_reward0p987__comparison_opus48_vs_gpt55__good_vs_truth.png) | GPT-5.5 | 0.149 | [`DBEVAL-V0-056_gpt55_reward0p149__comparison_opus48_vs_gpt55__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-056_gpt55_reward0p149__comparison_opus48_vs_gpt55__bad_vs_truth.png) | [`opus48_vs_gpt55_DBEVAL-V0-056_overlay.png`](overlays/opus48_vs_gpt55_DBEVAL-V0-056_overlay.png) | [`opus48_vs_gpt55_DBEVAL-V0-056_triptych.png`](triptychs/opus48_vs_gpt55_DBEVAL-V0-056_triptych.png) |
| DBEVAL-V0-050 | Opus 4.8 | 0.731 | [`DBEVAL-V0-050_opus48_reward0p731__comparison_opus48_vs_gpt55__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-050_opus48_reward0p731__comparison_opus48_vs_gpt55__good_vs_truth.png) | GPT-5.5 | 0.150 | [`DBEVAL-V0-050_gpt55_reward0p150__comparison_opus48_vs_gpt55__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-050_gpt55_reward0p150__comparison_opus48_vs_gpt55__bad_vs_truth.png) | [`opus48_vs_gpt55_DBEVAL-V0-050_overlay.png`](overlays/opus48_vs_gpt55_DBEVAL-V0-050_overlay.png) | [`opus48_vs_gpt55_DBEVAL-V0-050_triptych.png`](triptychs/opus48_vs_gpt55_DBEVAL-V0-050_triptych.png) |
| DBEVAL-V0-058 | Opus 4.8 | 0.694 | [`DBEVAL-V0-058_opus48_reward0p694__comparison_opus48_vs_gpt55__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-058_opus48_reward0p694__comparison_opus48_vs_gpt55__good_vs_truth.png) | GPT-5.5 | 0.170 | [`DBEVAL-V0-058_gpt55_reward0p170__comparison_opus48_vs_gpt55__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-058_gpt55_reward0p170__comparison_opus48_vs_gpt55__bad_vs_truth.png) | [`opus48_vs_gpt55_DBEVAL-V0-058_overlay.png`](overlays/opus48_vs_gpt55_DBEVAL-V0-058_overlay.png) | [`opus48_vs_gpt55_DBEVAL-V0-058_triptych.png`](triptychs/opus48_vs_gpt55_DBEVAL-V0-058_triptych.png) |
| DBEVAL-V0-053 | Opus 4.8 | 0.553 | [`DBEVAL-V0-053_opus48_reward0p553__comparison_opus48_vs_gpt54mini__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-053_opus48_reward0p553__comparison_opus48_vs_gpt54mini__good_vs_truth.png) | GPT-5.4 mini | 0.031 | [`DBEVAL-V0-053_gpt54mini_reward0p031__comparison_opus48_vs_gpt54mini__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-053_gpt54mini_reward0p031__comparison_opus48_vs_gpt54mini__bad_vs_truth.png) | [`opus48_vs_gpt54mini_DBEVAL-V0-053_overlay.png`](overlays/opus48_vs_gpt54mini_DBEVAL-V0-053_overlay.png) | [`opus48_vs_gpt54mini_DBEVAL-V0-053_triptych.png`](triptychs/opus48_vs_gpt54mini_DBEVAL-V0-053_triptych.png) |
| DBEVAL-V0-059 | Opus 4.8 | 0.539 | [`DBEVAL-V0-059_opus48_reward0p539__comparison_opus48_vs_gpt54mini__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-059_opus48_reward0p539__comparison_opus48_vs_gpt54mini__good_vs_truth.png) | GPT-5.4 mini | 0.043 | [`DBEVAL-V0-059_gpt54mini_reward0p043__comparison_opus48_vs_gpt54mini__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-059_gpt54mini_reward0p043__comparison_opus48_vs_gpt54mini__bad_vs_truth.png) | [`opus48_vs_gpt54mini_DBEVAL-V0-059_overlay.png`](overlays/opus48_vs_gpt54mini_DBEVAL-V0-059_overlay.png) | [`opus48_vs_gpt54mini_DBEVAL-V0-059_triptych.png`](triptychs/opus48_vs_gpt54mini_DBEVAL-V0-059_triptych.png) |
| DBEVAL-V0-048 | GPT-5.4 | 0.548 | [`DBEVAL-V0-048_gpt54_reward0p548__comparison_gpt54_vs_gpt54mini__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-048_gpt54_reward0p548__comparison_gpt54_vs_gpt54mini__good_vs_truth.png) | GPT-5.4 mini | 0.122 | [`DBEVAL-V0-048_gpt54mini_reward0p122__comparison_gpt54_vs_gpt54mini__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-048_gpt54mini_reward0p122__comparison_gpt54_vs_gpt54mini__bad_vs_truth.png) | [`gpt54_vs_gpt54mini_DBEVAL-V0-048_overlay.png`](overlays/gpt54_vs_gpt54mini_DBEVAL-V0-048_overlay.png) | [`gpt54_vs_gpt54mini_DBEVAL-V0-048_triptych.png`](triptychs/gpt54_vs_gpt54mini_DBEVAL-V0-048_triptych.png) |
| DBEVAL-V0-047 | GPT-5.4 | 0.501 | [`DBEVAL-V0-047_gpt54_reward0p501__comparison_gpt54_vs_gpt5__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-047_gpt54_reward0p501__comparison_gpt54_vs_gpt5__good_vs_truth.png) | GPT-5 | 0.138 | [`DBEVAL-V0-047_gpt5_reward0p138__comparison_gpt54_vs_gpt5__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-047_gpt5_reward0p138__comparison_gpt54_vs_gpt5__bad_vs_truth.png) | [`gpt54_vs_gpt5_DBEVAL-V0-047_overlay.png`](overlays/gpt54_vs_gpt5_DBEVAL-V0-047_overlay.png) | [`gpt54_vs_gpt5_DBEVAL-V0-047_triptych.png`](triptychs/gpt54_vs_gpt5_DBEVAL-V0-047_triptych.png) |
| DBEVAL-V0-045 | Opus 4.8 | 0.345 | [`DBEVAL-V0-045_opus48_reward0p345__comparison_opus48_vs_gpt4o__good_vs_truth.png`](individual_by_comparison/DBEVAL-V0-045_opus48_reward0p345__comparison_opus48_vs_gpt4o__good_vs_truth.png) | GPT-4o | 0.030 | [`DBEVAL-V0-045_gpt4o_reward0p030__comparison_opus48_vs_gpt4o__bad_vs_truth.png`](individual_by_comparison/DBEVAL-V0-045_gpt4o_reward0p030__comparison_opus48_vs_gpt4o__bad_vs_truth.png) | [`opus48_vs_gpt4o_DBEVAL-V0-045_overlay.png`](overlays/opus48_vs_gpt4o_DBEVAL-V0-045_overlay.png) | [`opus48_vs_gpt4o_DBEVAL-V0-045_triptych.png`](triptychs/opus48_vs_gpt4o_DBEVAL-V0-045_triptych.png) |

## Notes

- `truth` is the green reference structure inside every render.
- In pair renders, the higher-scoring model is orange and the lower-scoring model is blue.
- The same Opus 4.8 render for `DBEVAL-V0-056` appears in two comparisons, which is why the deduplicated folder has 17 images while the per-comparison folder has 18.
