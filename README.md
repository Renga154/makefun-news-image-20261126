[![make.fun](https://make.fun/badge/news-image-20261126.svg)](https://make.fun/bounty/news-image-20261126?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261126) [![rank](https://make.fun/badge/news-image-20261126/Renga154/makefun-news-image-20261126/rank.svg)](https://make.fun/bounty/news-image-20261126/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261126) [![reward](https://make.fun/badge/news-image-20261126/Renga154/makefun-news-image-20261126/reward.svg)](https://make.fun/bounty/news-image-20261126?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261126)

# THE WORLD TODAY

**Thursday 26 November 2026** · **16 stories · 9 regions · 12 fields**

This typeset front page pairs a colour-coded coverage strip with a UTC timeline of report times and snapshots. Pins on the numbered dot-grid world map match the lead cards and briefs.

## Lead stories

1. **Houthis strike Saudi ports as oil surges.** Brent settled 3.5% higher at $94.61 on 25 November and traded at $94.81 on Thursday. Iran’s Revolutionary Guards said two tankers hit mines near the Strait of Hormuz. Reuters could not independently verify the claim.
2. **Thanksgiving storm cuts power to more than 836,000 customers.** Macy’s Thanksgiving Day Parade moved to Saturday in its first weather postponement in 100 years.
3. **A record 2,100-plus migrants reach the Canary Islands.** Fifteen boats arrived within 24 hours, mostly on El Hierro. The 26 November update put the island’s monthly arrivals at 15,025, above its roughly 12,000 residents.
4. **Two Italian technicians die in a drone attack in Kuwait.** The Rheinmetall Italia staff worked at an air-defence station. Kuwait blamed Iran, which denied responsibility.

## World briefs

5. Israeli strikes and gunfire kill 10 in Gaza.
6. Ukrainian drones hit Russia’s Slavyansk refinery overnight.
7. Cairo detains the driver over the 25 November tanker crash that killed 31.
8. China–Cambodia Golden Dragon drills run from 25 November to 9 December.
9. Guinea-Bissau delays elections to November 2028.
10. Trump demands an investigation into pre-midterm US GDP figures.
11. An Indonesian mine flood leaves eight dead and 18 trapped.
12. Norse Atlantic suspends flights and flags bankruptcy risk.
13. North Korea expels the Swiss envoy on 25 November, reported in 26 November editions.
14. Fresh protests follow a 36% increase in Bangladesh’s garment minimum wage.
15. Australia and the Solomon Islands signed a pact worth A$740 million on 25 November.
16. Colombia revises the Cartagena siege count to 76 captives.

## DATE CHECK - EXCLUDED

- Huawei verdict · The New York jury ruled on 24 November.
- UN AI framework call · The call was made on 23 November.
- Chen Jining probe · The investigation was announced on 24 November.
- Cairo tanker crash · The crash occurred on the evening of 25 November. The brief covers the driver’s detention on 26 November.
- Saudi strike on Hodeidah · The strike took place on 25 November.
- Shenzhou-24, Trump tariffs and the Asian market plunge · All appeared in the 25 November entry.

The edition draws on Reuters, AP, AFP and other reporting through 26 November 2026 UTC. Every item was date-checked. Earlier events are dated in context, and each story counts once by primary region and field.

## Build and run

[build/svg-data.json](build/svg-data.json) contains the page content. [build/render-svg.py](build/render-svg.py) typesets it as SVG using Liberation fonts and Pillow text measurements, rasterises it to PNG with FFmpeg, and writes the 1024 × 1024 [entry.jpg](entry.jpg).

Run the entry with `entry.jpg` beside `main.py`.

```sh
python3 main.py
```

The standard-library script runs offline. It checks the JPEG signature, dimensions and 1 MiB size limit, then copies the bytes to `/output/entry.png`. If that path cannot be written, it uses `./output/entry.png`. The file retains its JPEG encoding. The script reads the destination back, checks its SHA-256 against the source, and prints the path, byte count and full digest.
