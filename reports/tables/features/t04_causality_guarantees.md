**Table — Adversarial causality checks G1, G2, G4, G5 and G6 executed on the real development history.**

| symbol | guarantee | statistic | value | passes |
| --- | --- | --- | --- | --- |
| BTCUSDT | G1 prefix invariance | max |full[:cut] - prefix| | 0 | True |
| BTCUSDT | G2 future-mutation invariance | max |clean[:cut] - corrupted[:cut]| | 0 | True |
| BTCUSDT | G4 shift applied exactly once (lag=1) | max |built - manually lagged| | 0 | True |
| BTCUSDT | G5 no infinities | count of +/-inf | 0 | True |
| BTCUSDT | G6 determinism | frame equality on rebuild | 1 | True |
| ETHUSDT | G1 prefix invariance | max |full[:cut] - prefix| | 0 | True |
| ETHUSDT | G2 future-mutation invariance | max |clean[:cut] - corrupted[:cut]| | 0 | True |
| ETHUSDT | G4 shift applied exactly once (lag=1) | max |built - manually lagged| | 0 | True |
| ETHUSDT | G5 no infinities | count of +/-inf | 0 | True |
| ETHUSDT | G6 determinism | frame equality on rebuild | 1 | True |
