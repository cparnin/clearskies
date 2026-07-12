# Clear Skies Tonight

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
- `PRIME_END_HOUR` - Before-midnight cutoff for the prime-time bonus (default: 24 = midnight)
- `TYPE_WEIGHTS` - Object type preference (default favors galaxies, mostly ignores clusters)
- `MIN_TARGET_SCORE` - Minimum score to show targets (default: 6/10)
- `TOP_TARGETS_COUNT` - Targets per notification section (default: 8)

**3. Install ntfy app and subscribe to your topic**

**4. Test**
```bash
python main.py --dry-run   # prints the notification without sending it
python main.py             # the real thing
```

For automated runs via GitHub Actions, set `LATITUDE`, `LONGITUDE`, and `NTFY_TOPIC` as repository secrets.

---

## How It Works

Runs daily at 4/5 PM ET (GitHub Actions), evaluates:
- Weather hour-by-hour across the whole night (finds the best clear stretch, not just an evening snapshot)
- Moon phase and position, checked at each target's own peak time
- 89 deep sky targets scored on their peak altitude between darkness and dawn

Sends a push notification if conditions score 6+ and good targets exist. Targets are
split into two sections: peaking **before midnight** (attended imaging) and
**overnight** (set up the DWARF3 and leave it out).

If the evening is cloudy but the sky clears later, you still get notified, with a
note like "clears ~1 AM". A night with no 2-hour clear stretch never notifies.

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
| Prime Time | 0.5 | Full bonus if it peaks before midnight, -0.15/hour after |

**Key features:**
- The observing window runs from darkness (sunset + 2h) to dawn — late peaks are
  never dropped, just weighted toward before-midnight and grouped separately
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
