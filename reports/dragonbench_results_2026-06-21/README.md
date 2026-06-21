# DragonBench Results Pack

Generated: 2026-06-21T11:26:54

This is the commit-ready analysis folder. It intentionally excludes bulky raw HUD trace-event JSON caches while keeping the CSV tables, Markdown analysis, plots, and curated protein-fold render images needed to reproduce the presentation figures.

## What Is Included

- `data/`: CSV data tables used by the plots and analysis.
- `plots/`: regenerated summary plots.
- `protein_fold_renders/`: unannotated render-only PNGs plus image indexes for the protein-fold comparisons.
- `HUD_JOBS.md`: HUD job IDs for the original run, TF rerun, and retries.

## Main Updated Leaderboard

This leaderboard uses the original 100-question Modal full run, with the DragonTFBind slice replaced by the latest 20-question TF rerun.

| Model | Rows | Updated mean reward | Completed | Error rows | Nonzero | Original mean | Delta vs original |
|---|---:|---:|---:|---:|---:|---:|---:|
| Opus 4.8 | 100 | 0.3376 | 100 | 0 | 58 | 0.3421 | -0.0045 |
| Gemini 3.1 Pro | 100 | 0.3213 | 74 | 26 | 50 | 0.2622 | +0.0592 |
| GPT-5.5 | 100 | 0.2546 | 86 | 14 | 59 | 0.2600 | -0.0054 |
| GPT-5 | 100 | 0.2175 | 99 | 1 | 58 | 0.2002 | +0.0173 |
| GPT-5.4 | 100 | 0.2106 | 100 | 0 | 55 | 0.2108 | -0.0002 |
| GPT-4o | 100 | 0.1566 | 99 | 1 | 48 | 0.2406 | -0.0840 |
| GPT-5.4 mini | 100 | 0.1222 | 99 | 1 | 52 | 0.1805 | -0.0582 |

## Latest DragonTFBind Rerun

| Model | Mean reward | Completed | Error rows | Nonzero |
|---|---:|---:|---:|---:|
| Gemini 3.1 Pro | 0.6616 | 19/20 | 1 | 18 |
| Opus 4.8 | 0.6531 | 20/20 | 0 | 18 |
| GPT-5.5 | 0.5766 | 20/20 | 0 | 16 |
| GPT-5 | 0.5213 | 20/20 | 0 | 15 |
| GPT-5.4 | 0.3788 | 20/20 | 0 | 15 |
| GPT-4o | 0.3162 | 20/20 | 0 | 13 |
| GPT-5.4 mini | 0.2204 | 20/20 | 0 | 14 |

## Error Reruns

Second retry jobs were still active when this pack was generated; see `HUD_JOBS.md` and `data/error_retry_summary.csv`.

| Retry pass | Model | Rows | Completed | Errors | Running | Mean reward |
|---|---|---:|---:|---:|---:|---:|
| first_retry | Gemini 3.1 Pro | 34 | 1 | 33 | 0 | 0.0294 |
| first_retry | GPT-4o | 1 | 1 | 0 | 0 | 0.0030 |
| first_retry | GPT-5 | 1 | 1 | 0 | 0 | 0.1290 |
| first_retry | GPT-5.4 mini | 1 | 1 | 0 | 0 | 0.0829 |
| first_retry | GPT-5.5 | 14 | 13 | 1 | 0 | 0.3451 |
| second_retry_active | Gemini 3.1 Pro | 3 | 0 | 0 | 3 | 0.0000 |
| second_retry_active | GPT-5.5 | 1 | 0 | 0 | 1 | 0.0000 |

## Protein Fold Render Images

The organized render folder is `protein_fold_renders/`. The key file is `protein_fold_renders/IMAGE_INDEX.md`, which maps each comparison to the exact filenames.

Protein summary from the original full run:

| Model | Mean protein reward | Best | Nonzero | Valid JSON | PDB answers |
|---|---:|---:|---:|---:|---:|
| Opus 4.8 | 0.3008 | 0.9873 | 16 | 20 | 20 |
| GPT-5.4 | 0.2612 | 0.7208 | 20 | 20 | 20 |
| GPT-5.4 mini | 0.1300 | 0.2917 | 19 | 19 | 19 |
| GPT-5 | 0.1152 | 0.1696 | 19 | 19 | 19 |
| GPT-4o | 0.0860 | 0.3682 | 16 | 19 | 19 |
| GPT-5.5 | 0.0839 | 0.1696 | 16 | 20 | 10 |
| Gemini 3.1 Pro | 0.0000 | 0.0000 | 0 | 0 | 0 |

## Recommended Plots

- `plots/updated_full_run_model_scores.png`
- `plots/original_vs_updated_full_run_model_scores.png`
- `plots/updated_family_reward_heatmap.png`
- `plots/latest_tf_and_retries/tf_bench_rerun_model_scores.png`
- `plots/latest_tf_and_retries/tf_bench_original_vs_rerun.png`
- `plots/latest_tf_and_retries/error_retry_status.png`

## Notes

- The updated composite is not a brand-new 100-task rerun. It is the original full run with DragonTFBind replaced by the latest TF rerun after the repository update.
- Gemini's TF rerun had one provider error row but still carried a numeric reward in HUD.
- Gemini's first retry pass for previous errors mostly failed with gateway/provider errors; the second retry pass was active when this folder was packaged.
