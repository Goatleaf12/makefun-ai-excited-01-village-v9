[![make.fun · ai-excited-01](https://make.fun/badge/ai-excited-01.svg)](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)
[![rank](https://make.fun/badge/ai-excited-01/Goatleaf12/makefun-ai-excited-01-village-v9/rank.svg)](https://make.fun/bounty/ai-excited-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)
[![reward](https://make.fun/badge/ai-excited-01/Goatleaf12/makefun-ai-excited-01-village-v9/reward.svg)](https://make.fun/bounty/ai-excited-01?utm_source=github&utm_medium=readme&utm_campaign=ai-excited-01)

# The Village That Sailed the Sky

A 1024x1024 poster drawn from scratch in pure Python (standard library
only — no network, no input files, no third-party packages).

The scene: a luminous floating village — warm-lit houses on a rock
island adrift in the clouds — with a waterfall pouring off the island's
edge into a sea of clouds below, one large sailing ship in the
foreground before a rising sun, one small distant ship on the horizon,
birds, god-rays, and a two-line caption inside the image.

## Run

```sh
python3 main.py
```

The image is written to `$OUTPUT_PATH`, else
`$MAKEFUN_OUTPUT_DIR/entry.png`, else `/output/entry.png`.

## Determinism

Fixed seed `20261117`, no clock, no network: two runs write
byte-identical PNG files.

## License

MIT — see `LICENSE`.
