# HUD Job IDs

## Original Modal full run

| Model | Job ID |
|---|---|
| Opus 4.8 | `d0785f45-515b-4721-aa3c-d948dc5dd0f2` |
| Gemini 3.1 Pro | `a22bf38c-950f-482d-88b7-8f471a6d2c57` |
| GPT-5.5 | `b4407a3e-477b-4933-83fb-96ff3213ca5c` |
| GPT-5.4 | `959ae140-50d8-4d2a-ad2d-b2f8ee71628c` |
| GPT-5.4 mini | `f2e5a6ab-054a-4b34-889f-33b8890dc11f` |
| GPT-5 | `9c2a4fe7-68a4-42b4-a9da-06db80b501b9` |
| GPT-4o | `0f5e7425-9d0d-496e-b1cd-9aa4e1fa6c77` |

The original jobs are not exported as separate old-data CSVs in this pack. They are only the baseline rows that remain where no newer rerun exists.

## Latest DragonTFBind rerun

| Model | Job ID |
|---|---|
| Opus 4.8 | `3077ca83-2ef4-4613-90e2-206dac3686ea` |
| Gemini 3.1 Pro | `5d9c1a9f-aa0b-4b75-a9c1-c4244c1dea7d` |
| GPT-5.5 | `08e86b1e-ecac-459f-9ee6-d29cd9c82d4d` |
| GPT-5.4 | `0a757ea7-30fa-42aa-9dfd-1aa248ee4304` |
| GPT-5.4 mini | `c4352fc5-82b3-4d24-b611-3950e78602e5` |
| GPT-5 | `5967cd92-82f5-43c5-8160-13ecbe6c9b44` |
| GPT-4o | `5b62a4b9-7b5e-426e-bc31-b3f3d6ef02ce` |

## Error reruns

| Pass | Model | Job ID | Status at regeneration |
|---|---|---|---|
| first_retry | GPT-4o | `cb1307c0-5117-43ab-81e2-179910f90711` | 1 completed |
| first_retry | GPT-5 | `6326a0df-0293-44ec-bd34-4b3cd4f39774` | 1 completed |
| first_retry | GPT-5.4 mini | `418eac38-d4ee-4916-8854-270e844626d6` | 1 completed |
| first_retry | GPT-5.5 | `b795fe7a-4d40-4948-989a-9577dfd331e0` | 13 completed, 1 error |
| first_retry | Gemini 3.1 Pro | `3b6fb416-2a59-4e0d-84f6-b2b8b810475e` | 1 completed, 33 error |
| second_retry | GPT-5.5 | `5dc63e61-0eae-452b-b1b0-5dc74e341f0d` | 1 completed |
| second_retry | Gemini 3.1 Pro | `884f6899-ad6f-4ea6-a8b3-948528d3de4f` | 3 running |
