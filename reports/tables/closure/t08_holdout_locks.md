**Table — Independent controls preventing publication of the frozen-holdout reading.**

| control | state | verified |
| --- | --- | --- |
| Artifact layer | study_dashboard.json contains no holdout metrics unless --include-holdout is passed | True |
| Service layer | publication requires PERP_LAB_HOLDOUT_PUBLICATION == AUDITED_OPEN_FINAL_HOLDOUT | True |
| This notebook | reads no holdout metrics; multiple-testing artifact confirms holdout_accessed = False | True |
