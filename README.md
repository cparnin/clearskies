# ClearSkies

Push notifications for optimal astrophotography conditions with DWARF3.

## Setup

**1. Install dependencies** (Python 3.10+)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure `config.py`**

Required changes:
- `LATITUDE` / `LONGITUDE` - Your observing location
- `TIMEZONE` - Your timezone (see [tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones))
- `NTFY_TOPIC` - Your notification topic (env var / repo secret). Make it hard to guess, e.g. `clearskies-` plus random characters: anyone who knows it can read and send to it

Optional:
- `NTFY_SERVER` - Self-hosted ntfy server URL (default: `https://ntfy.sh`); set `NTFY_TOKEN` too if it requires auth
- `HORIZON_MASK` - Azimuth wedges your local horizon blocks (trees, buildings); see [Customization](#customization)
- `MIN_ALTITUDE` - Lowest altitude worth shooting (default: 30°)
- `TARGET_TYPES` - Object types to consider at all (default: `galaxy`; e.g. `galaxy,cluster` to add clusters back)
- `PRIME_END_HOUR` - Attended-imaging cutoff for the prime-time bonus (default: 23 = 11 PM)
- `SN_MAX_MAG` - Faintest supernova or Andromeda nova worth an alert (default: 15; `0` turns these alerts off)
- `TYPE_WEIGHTS` - Preference among `TARGET_TYPES` (default favors galaxies, mostly ignores clusters)
- `MIN_TARGET_SCORE` - Minimum score to show targets (default: 6/10)
- `TOP_TARGETS_COUNT` - Targets per notification (default: 3)

**3. Install ntfy app and subscribe to your topic**

**4. Test**
```bash
python tests.py            # offline sanity checks (also run in CI)
python main.py --dry-run   # prints the notification without sending it
python main.py             # the real thing
```

For automated runs via GitHub Actions, set `LATITUDE`, `LONGITUDE`, and `NTFY_TOPIC` as repository secrets (plus `NTFY_SERVER` / `NTFY_TOKEN` if you self-host ntfy). `TIMEZONE`, `HORIZON_MASK`, `MIN_ALTITUDE`, `TARGET_TYPES`, and `SN_MAX_MAG` can be set as repository variables. Unset values fall back to the defaults in `config.py` — including the author's location, so set your own.

---

## How It Works

Runs daily in the late afternoon ET (GitHub Actions; a late-starting run still plans that evening), evaluates:
- Weather hour-by-hour across the whole night (finds the best clear stretch, not just an evening snapshot)
- Moon phase and position, checked at each target's own best time
- Deep sky targets (of the `TARGET_TYPES` you want) scored at their highest point
  in the part of the sky your site can see, between astronomical darkness
  (sun 18° below the horizon) and astronomical dawn

Sends a push notification if conditions score 6+ and good targets exist, listing
the **top 3 targets** for the night, plus any **exploding stars** in your visible
sky: up to two bright supernovae and a bright nova in Andromeda (see
[Exploding stars](#exploding-stars)). Targets peaking after the prime cutoff are
tagged "(overnight, leave it out)".

The moon is a first-class gate: the conditions penalty scales with phase *and*
with how much of the clear stretch is moonlit. A bright moon (>80%) up all night
costs 5 points — enough to suppress the notification on its own — while one
that sets early in the stretch barely registers. Full-moon nights stay silent.

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
| Altitude | 3.0 | Highest altitude reached in your visible sky during the night (30-75° optimal) |
| Moon | 3.5 | Phase-first, evaluated at the target's best time (moon down = max; separation only softens a bright moon, never rescues it) |
| Type | 1.5 | Galaxy = 1.5, Nebula = 0.5 (showpieces = 1.5), Cluster = 0.2 |
| Difficulty | 1.0 | Easy = 1.0, Medium = 0.8, Hard = 0.5 |
| FOV Fit | 0.5 | How well target fits DWARF3's 3° FOV (0.3-2.0° optimal) |
| Prime Time | 0.5 | Full bonus if it peaks before the `PRIME_END_HOUR` cutoff, -0.15/hour after |

**Key features:**
- The observing window runs from astronomical darkness (sun 18° below the
  horizon) to astronomical dawn — late peaks are never dropped, just weighted
  toward before-midnight and tagged "(overnight)"
- A target that reaches 80%+ of its peak altitude by the prime cutoff (and is
  unblocked there) counts as a before-midnight target, evaluated at the cutoff —
  the overnight tag is reserved for targets where leaving the scope out actually
  buys real altitude
- Each target's track is sampled every 10 minutes across the night and scored at
  its highest point outside `HORIZON_MASK` and above `MIN_ALTITUDE`. With only the
  east open, a target that transits due south is scored on its climb, just
  before it crosses into the blocked west — not dropped for peaking there
- A target that never enters your visible sky tonight is dropped entirely, not
  penalized — a blocked target is not a weak target
- Moon interference is computed at each target's best time, so a moonrise at 2 AM
  only penalizes the targets that are best after 2 AM

---

## Target Catalog

107 targets optimized for DWARF3's 3° field of view:
**41 galaxies, 44 nebulae, 22 clusters**
(only galaxies are recommended by default — see `TARGET_TYPES`)

- **Winter** - Orion, Auriga, Monoceros: M42, Rosette, Horsehead, Jellyfish, Thor's Helmet
- **Spring** - Galaxy season: M81/82, M51, Leo Triplet, Needle, Whale, Southern Pinwheel, Markarian's Chain, Centaurus A
- **Summer** - Milky Way core: Lagoon, Trifid, Eagle, North America, Veil, Fireworks Galaxy
- **Fall** - Cassiopeia, Andromeda: M31, M33, Heart/Soul, Iris, Wizard, Silver Sliver, Sculptor
- **Odd & interacting galaxies** - Antennae, Whale & Hockey Stick, Cocoon, Siamese Twins,
  polar rings (Helix Galaxy, NGC 660), Splinter, Spindle, Draco Trio, Dusty Hand, and the
  Coma, Hercules, and Perseus galaxy clusters
- **Year-round** - M13, M92, M5 globulars

**Add targets** - Edit `DSO_CATALOG` in `targets.py`:
```python
("Name", "RA", "Dec", "type", "difficulty", size_degrees)
# Types: nebula, galaxy, cluster
# Difficulty: easy, medium, hard
# Size: apparent size in degrees (for FOV fit scoring)
```

---

## Exploding stars

When a notification goes out, ClearSkies also checks David Bishop's
[Latest Supernovae](https://www.rochesterastronomy.org/supernova.html) page
(updated daily from TNS and ATel) and adds a **💥 Exploding stars** section with
up to two supernovae, brightest first:

- Classified supernovae only (Ia, II, Ib/c, ...), no unconfirmed transients or novae
- Latest magnitude at or brighter than `SN_MAX_MAG` (default 15), observed within
  the last month
- Up in your visible sky (`HORIZON_MASK`, `MIN_ALTITUDE`) during tonight's clear
  stretch, with the best time to shoot it

Positions are the host galaxy's, which is what you frame.

It also checks the [Extragalactic Novae](https://www.rochesterastronomy.org/novae.html)
page for a nova in the Andromeda Galaxy (M31) at or brighter than `SN_MAX_MAG`,
measured within the last week, and lists the brightest one when M31 is in your
visible sky. Expect these rarely: most Andromeda novae peak around magnitude
16-19, beyond the DWARF3. A true supernova in Andromeda would come through the
supernova check.

If a page can't be fetched or parsed, the notification just goes out without
those lines. Run `python supernovae.py` to see tonight's picks.

---

## Customization

**Local horizon** - `HORIZON_MASK` in `config.py` is a list of
`(az_start, az_end, min_alt_deg)` wedges describing sky your site can't see.
A target peaking inside a wedge below its minimum altitude is dropped from the
recommendations entirely. Azimuth ranges may wrap through north — `(340, 20, 35)`
is valid. Set `[]` if your whole horizon is clear. The default,
`[(180, 360, 90)]`, blocks the entire western half — the author's usable sky is
the east, horizon to zenith. As an env var: `HORIZON_MASK="250-340:90,340-20:35"`.
`MIN_ALTITUDE` (default 30°) is a global floor applied everywhere, masked or not.

**Object types** - `TARGET_TYPES` (env var / repo variable, comma-separated) picks
which of `galaxy`, `cluster`, `nebula` are considered at all; anything else never
shows up. The default is `galaxy` only; `TARGET_TYPES=galaxy,cluster` adds clusters
back as low-weight filler.

**Object preferences** - Adjust `TYPE_WEIGHTS` in `config.py` (points out of 10)

**Later prime cutoff** - Set `PRIME_END_HOUR = 25` for a 1 AM cutoff

**Thresholds** - Adjust `MIN_TARGET_SCORE` (try 5.5 for more targets, 7 for fewer)

---

## Troubleshooting

**No notifications?**
- Run `python main.py --dry-run` locally to see the scores and decision
- Confirm ntfy topic matches between `config.py` and phone app
- Self-hosting? Make sure the app is subscribed on your server, not ntfy.sh, and that `NTFY_TOKEN` is set if the server requires auth

**Wrong targets?**
- Check `LATITUDE`/`LONGITUDE` are correct
- Targets are scored at their highest point in your visible sky during the night, not at sunset
- Missing a target you expected? It may be filtered by `TARGET_TYPES` or dropped by
  `HORIZON_MASK` / `MIN_ALTITUDE`

---

Built by [Chad Parnin](https://chadparnin.com).
