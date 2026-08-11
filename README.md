# ClearSkies

Push notifications for optimal astrophotography conditions with DWARF3.

## Setup

**1. Install dependencies**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure `config.py`**

Required changes:
- `LATITUDE` / `LONGITUDE` - Your observing location
- `TIMEZONE` - Your timezone (see [tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones))
- `NTFY_TOPIC` - Your unique notification topic

Optional:
- `HORIZON_MASK` - Azimuth wedges your local horizon blocks (trees, buildings); see [Customization](#customization)
- `MIN_ALTITUDE` - Drop targets peaking below this altitude (default: 30°)
- `PRIME_END_HOUR` - Attended-imaging cutoff for the prime-time bonus (default: 23 = 11 PM)
- `TYPE_WEIGHTS` - Object type preference (default favors galaxies, mostly ignores clusters)
- `MIN_TARGET_SCORE` - Minimum score to show targets (default: 6/10)
- `TOP_TARGETS_COUNT` - Targets per notification section (default: 5; ties with the last slot are kept)

**3. Install ntfy app and subscribe to your topic**

**4. Test**
```bash
python tests.py            # offline sanity checks (also run in CI)
python main.py --dry-run   # prints the notification without sending it
python main.py             # the real thing
```

For automated runs via GitHub Actions, set `LATITUDE`, `LONGITUDE`, and `NTFY_TOPIC` as repository secrets.

---

## How It Works

Runs daily at 4/5 PM ET (GitHub Actions), evaluates:
- Weather hour-by-hour across the whole night (finds the best clear stretch, not just an evening snapshot)
- Moon phase and position, checked at each target's own peak time
- 89 deep sky targets scored on their peak altitude between astronomical darkness
  (sun 18° below the horizon) and astronomical dawn

Sends a push notification if conditions score 6+ and good targets exist. Targets are
split into two sections: peaking **before midnight** (attended imaging) and
**overnight** (set up the DWARF3 and leave it out).

Targets are scored against the hours the sky is actually clear: if the evening is
cloudy but it clears at 1 AM, the notification says so ("clears ~1 AM", with a
`Clear:` window line) and recommends what peaks *during* the clearing - not what
would have peaked under the clouds. A night with no 2-hour clear stretch never
notifies.

---

## Scoring System

Targets scored 0-10 based on tonight's conditions (6+ threshold):

| Component | Points | Description |
|-----------|--------|-------------|
| Altitude | 3.0 | Peak altitude within the night (30-75° optimal) |
| Moon | 3.5 | Separation + phase, evaluated at the target's peak time (moon down = max) |
| Type | 1.5 | Galaxy = 1.5, Nebula = 1.0, Cluster = 0.2 |
| Difficulty | 1.0 | Easy = 1.0, Medium = 0.8, Hard = 0.5 |
| FOV Fit | 0.5 | How well target fits DWARF3's 3° FOV (0.3-2.0° optimal) |
| Prime Time | 0.5 | Full bonus if it peaks before the `PRIME_END_HOUR` cutoff, -0.15/hour after |

**Key features:**
- The observing window runs from astronomical darkness (sun 18° below the
  horizon) to astronomical dawn — late peaks are never dropped, just weighted
  toward before-midnight and grouped separately
- A target that reaches 80%+ of its peak altitude by the prime cutoff (and is
  unblocked there) counts as a before-midnight target, evaluated at the cutoff —
  "Overnight" is reserved for targets where leaving the scope out actually buys
  real altitude
- Targets whose peak lands behind a `HORIZON_MASK` wedge or below `MIN_ALTITUDE`
  are dropped entirely, not penalized — a blocked target is not a weak target
- Moon interference is computed at each target's peak time, so a moonrise at 2 AM
  only penalizes the targets that actually peak after 2 AM
- Setting targets are scored at the start of the window (their highest point),
  rising targets at whichever edge is higher

---

## Target Catalog

89 targets optimized for DWARF3's 3° field of view:
**23 galaxies, 44 nebulae, 22 clusters**

- **Winter** - Orion, Auriga, Monoceros: M42, Rosette, Horsehead, Jellyfish, Thor's Helmet
- **Spring** - Galaxy season: M81/82, M51, Leo Triplet, Needle, Whale, Southern Pinwheel, Markarian's Chain, Centaurus A
- **Summer** - Milky Way core: Lagoon, Trifid, Eagle, North America, Veil, Fireworks Galaxy
- **Fall** - Cassiopeia, Andromeda: M31, M33, Heart/Soul, Iris, Wizard, Silver Sliver, Sculptor
- **Year-round** - M13, M92, M5 globulars

**Add targets** - Edit `DSO_CATALOG` in `targets.py`:
```python
("Name", "RA", "Dec", "type", "difficulty", size_degrees)
# Types: nebula, galaxy, cluster
# Difficulty: easy, medium, hard
# Size: apparent size in degrees (for FOV fit scoring)
```

---

## Customization

**Local horizon** - `HORIZON_MASK` in `config.py` is a list of
`(az_start, az_end, min_alt_deg)` wedges describing sky your site can't see.
A target peaking inside a wedge below its minimum altitude is dropped from the
recommendations entirely. Azimuth ranges may wrap through north — `(340, 20, 35)`
is valid. Set `[]` if your whole horizon is clear. The default,
`[(250, 340, 90)]`, blocks the WNW-NW sky (the author's house). As an env var:
`HORIZON_MASK="250-340:90,340-20:35"`. `MIN_ALTITUDE` (default 30°) is a global
floor applied everywhere, masked or not.

**Object preferences** - Adjust `TYPE_WEIGHTS` in `config.py` (points out of 10)

**Later prime cutoff** - Set `PRIME_END_HOUR = 25` for a 1 AM cutoff

**Thresholds** - Adjust `MIN_TARGET_SCORE` (try 5.5 for more targets, 7 for fewer)

---

## Troubleshooting

**No notifications?**
- Run `python main.py --dry-run` locally to see the scores and decision
- Confirm ntfy topic matches between `config.py` and phone app

**Wrong targets?**
- Check `LATITUDE`/`LONGITUDE` are correct
- Targets are scored at their peak altitude during the night, not at sunset
- Missing a target you expected? It may be dropped by `HORIZON_MASK` or `MIN_ALTITUDE`

---

Built by [Chad Parnin](https://chadparnin.com).
