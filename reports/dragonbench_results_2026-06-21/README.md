# DragonBench Results Pack

Generated: 2026-06-21T18:39:22Z

This folder contains the current DragonBench analysis dataset. Superseded rows are not included as standalone old-data tables: newer reruns are applied as row-level replacements inside `data/current_full_run_traces.csv`.

## Current Row-Level Dataset

- `data/current_full_run_traces.csv`: one current row per model/question, after row-level replacements.
- `data/current_full_run_summary.csv`: model-level summary from the current rows.
- `data/current_full_run_family_summary.csv`: task-family summary from the current rows.
- `data/current_full_run_task_difficulty.csv`: question-level summary from the current rows.
- `data/row_replacement_log.csv`: audit log of every replaced row.
- `data/rerun_attempts.csv`: retry/rerun attempt manifest, including second retries.

## Replacement Counts

| pass | source | rows |
| --- | --- | --- |
| first_retry | error_retry_terminal | 42 |
| second_retry | error_retry_terminal | 1 |
| tf_bench_rerun | tf_bench_rerun | 140 |

## Current Leaderboard

| model | rows | mean reward | completed | errors | running | nonzero | replaced rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Opus 4.8 | 100 | 0.3376 | 100 | 0 | 0 | 58 | 20 |
| Gemini 3.1 Pro | 100 | 0.3313 | 75 | 25 | 0 | 51 | 45 |
| GPT-5.5 | 100 | 0.3087 | 100 | 0 | 0 | 68 | 34 |
| GPT-5 | 100 | 0.2188 | 100 | 0 | 0 | 59 | 21 |
| GPT-5.4 | 100 | 0.2106 | 100 | 0 | 0 | 55 | 20 |
| GPT-4o | 100 | 0.1567 | 100 | 0 | 0 | 49 | 21 |
| GPT-5.4 mini | 100 | 0.1231 | 100 | 0 | 0 | 53 | 21 |

## Current Family Scores

| model | AnoleGeneParse | AnolePromoterExpression | KomodoProteinFold | DragonTFBind | RNAFold |
| --- | --- | --- | --- | --- | --- |
| Opus 4.8 | 0.6218 | 0.1125 | 0.3008 | 0.6531 | 0.0000 |
| Gemini 3.1 Pro | 0.6828 | 0.1342 | 0.0000 | 0.6616 | 0.1780 |
| GPT-5.5 | 0.5379 | 0.1450 | 0.0839 | 0.5766 | 0.2001 |
| GPT-5.4 | 0.2407 | 0.1725 | 0.2612 | 0.3788 | 0.0000 |
| GPT-5 | 0.2587 | 0.1358 | 0.1216 | 0.5213 | 0.0566 |
| GPT-4o | 0.3075 | 0.0733 | 0.0862 | 0.3162 | 0.0000 |
| GPT-5.4 mini | 0.1376 | 0.1233 | 0.1341 | 0.2204 | 0.0000 |

## Second Error Reruns

Second retry rows are incorporated in `data/rerun_attempts.csv`. GPT-5.5's second retry completed and replaced its remaining Anole row. Gemini's second retry rows are still running, so they are tracked but not scored yet.

| model | status | rows |
| --- | --- | --- |
| GPT-5.5 | completed | 1 |
| Gemini 3.1 Pro | running | 3 |

## Recommended Plots

- `plots/current_full_run_model_scores.png`
- `plots/current_family_reward_heatmap.png`
- `plots/current_task_family_grouped_bars.png`
- `plots/current_per_question_reward_matrix.png`
- `plots/current_completion_status.png`
- `plots/rerun_attempt_status.png`

## Protein Fold Render Images

The organized render folder is `protein_fold_renders/`. The key file is `protein_fold_renders/IMAGE_INDEX.md`, which maps each comparison to exact image filenames. The protein score CSVs in `data/` now use the current row-level replacement dataset.

The high-resolution render folder is `protein_fold_renders_high_res/`. A ranked markdown shortlist of the most useful good-vs-bad protein fold examples is `PROTEIN_FOLDING_INTERESTING_COMPARISONS.md`.

## Notes

- DragonTFBind rows are replaced by the latest TF bench rerun for all models/questions in that family.
- Terminal error-retry rows replace the original errored rows for non-TF tasks.
- Running second-retry rows are tracked in `data/rerun_attempts.csv` but are not scored until HUD returns terminal rows with rewards.
