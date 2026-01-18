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
- `MAX_OBSERVING_HOUR` - Latest hour to start imaging (default: 23 = 11 PM)
- `MIN_TARGET_SCORE` - Minimum score to show targets (default: 6/10)
- `TOP_TARGETS_COUNT` - Targets per notification (default: 10)

**3. Install ntfy app and subscribe to your topic**

**4. Test**
```bash
python main.py
```

For automated runs via GitHub Actions, set `LATITUDE`, `LONGITUDE`, and `NTFY_TOPIC` as repository secrets.

---

## How It Works

Runs daily at 4 PM EST, evaluates:
- Weather (cloud cover, humidity, wind)
- Moon phase, position, and interference
- 79 deep sky targets scored on peak altitude within your observing window

Sends push notification if conditions score 6+ and good targets exist.

---

## Scoring System

Targets scored 0-10 based on tonight's conditions (6+ threshold):

| Component | Points | Description |
|-----------|--------|-------------|
| Altitude | 3.0 | Peak altitude within observing window (30-70° optimal) |
| Moon Separation | 3.0 | Angular distance from moon (if moon is up) |
| Moon Phase | 1.5 | Moon brightness (only matters if <60° from target) |
| Difficulty | 1.5 | Easy=1.5, Medium=1.1, Hard=0.8 |
| Type Bonus | 0.5 | Galaxy=+0.5, Nebula=+0.2, Cluster=0 |
| FOV Fit | 0.5 | How well target fits DWARF3's 3° FOV (0.3-2.0° optimal) |

**Key features:**
- Scores at peak altitude during window, not just sunset (handles late-rising targets)
- Moon below horizon = automatic max points (no penalty)
- Window ends at: 11 PM, moon rise (if >50%), or dawn (whichever is earliest)

**Example scores:**

New moon, target at 38° altitude:
```
Rosette Nebula: 9.3/10
  Alt(3.0) + Moon(3.0) + Phase(1.5) + Diff(1.1) + Type(0.2) + FOV(0.5)
```

Half moon 40° away, target at 25°:
```
M42 Orion: 5.8/10 (below threshold, won't notify)
  Alt(1.5) + Moon(1.0) + Phase(1.1) + Diff(1.5) + Type(0.2) + FOV(0.5)
```

---

## Target Catalog

79 targets optimized for DWARF3's 3° field of view:

- **Winter (29)** - Orion, Auriga, Taurus: M42, Rosette, Horsehead, Pleiades
- **Spring (13)** - Galaxy season: M81/82, M51, Leo Triplet, M101
- **Summer (24)** - Milky Way core: Lagoon, Trifid, North America, Veil
- **Fall (10)** - Cassiopeia, Andromeda: M31, Heart/Soul, Elephant Trunk
- **Year-round (3)** - M13, M92, M5

Breakdown: 38 nebulae, 20 galaxies, 21 clusters

---

## Customization

**Scoring preferences** - Edit `targets.py` lines 368-374 to adjust type bonus

**Add targets** - Edit `DSO_CATALOG` in `targets.py`:
```python
("Name", "RA", "Dec", "type", "difficulty", size_degrees)
# Types: nebula, galaxy, cluster
# Difficulty: easy, medium, hard
# Size: optional, in degrees
```

**Thresholds** - Adjust `MIN_TARGET_SCORE` (try 5.5 for more targets, 7 for fewer)

---

## Troubleshooting

**No notifications?**
- Verify conditions score ≥6 (run `python main.py` locally to check)
- Confirm ntfy topic matches between `config.py` and phone app

**Wrong targets?**
- Check `LATITUDE`/`LONGITUDE` are correct
- Targets scored at peak altitude, not sunset

**Moon penalties on new moon?**
- Fixed - moon below horizon gives automatic max points
