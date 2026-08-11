"""Deep sky object target recommendations, scored for tonight's window."""

import ephem

from astro import fmt_time, get_night, make_observer, to_deg
from config import (
    DWARF3_OPTIMAL_TARGET_MAX, DWARF3_OPTIMAL_TARGET_MIN, HORIZON_MASK,
    LATE_PENALTY_PER_HOUR, MIN_ALTITUDE, MIN_TARGET_SCORE, TYPE_WEIGHTS,
)

PRIME_BONUS = 0.5  # points available for peaking before the prime cutoff
PRIME_USABLE_FRACTION = 0.8  # at the cutoff, this fraction of peak altitude counts as "already there"

# DWARF3-optimized catalog (telephoto ~3° x 1.65° FOV)
# Organized by season (when best visible in evening)
# Scoring handles visibility - add lots, let the algorithm pick what's best tonight
# Format: (name, RA, Dec, type, difficulty, size_degrees)
# RA in hours:minutes:seconds, Dec in degrees:minutes, size in degrees
DSO_CATALOG = [
    # === WINTER (Dec-Feb evening) ===
    # Orion region
    ("M42 - Orion Nebula", "5:35:16", "-5:23:28", "nebula", "easy", 1.0),
    ("M43 - De Mairan's Nebula", "5:35:31", "-5:16:03", "nebula", "easy", 0.3),
    ("IC 434 - Horsehead Region", "5:40:59", "-2:27:30", "nebula", "hard", 1.0),
    ("Flame Nebula", "5:41:54", "-1:51:12", "nebula", "medium", 0.5),
    ("M78 - Reflection Nebula", "5:46:46", "0:03:50", "nebula", "medium", 0.3),
    ("Barnard's Loop", "5:27:00", "-3:58:00", "nebula", "hard", 10.0),  # Huge, needs wide field
    ("Witch Head Nebula", "5:02:00", "-7:54:00", "nebula", "hard", 1.5),
    # Auriga/Gemini
    ("IC 405 - Flaming Star", "5:16:00", "34:21:00", "nebula", "medium", 0.5),
    ("IC 410 - Tadpole Nebula", "5:22:00", "33:24:00", "nebula", "medium", 0.5),
    ("IC 417 - Spider Nebula", "5:28:00", "34:25:00", "nebula", "medium", 0.4),
    ("IC 443 - Jellyfish Nebula", "6:17:13", "22:31:05", "nebula", "hard", 0.8),
    ("NGC 2174 - Monkey Head", "6:09:24", "20:29:34", "nebula", "medium", 0.7),
    ("M35 - Gemini Cluster", "6:09:00", "24:21:00", "cluster", "easy", 0.5),
    ("M36 - Pinwheel Cluster", "5:36:12", "34:08:24", "cluster", "easy", 0.2),
    ("M37 - Salt & Pepper", "5:52:18", "32:33:12", "cluster", "easy", 0.4),
    ("M38 - Starfish Cluster", "5:28:42", "35:51:18", "cluster", "easy", 0.3),
    # Monoceros/Canis Major
    ("Rosette Nebula", "6:33:45", "4:59:54", "nebula", "medium", 1.3),  # Perfect for DWARF3!
    ("Cone Nebula Region", "6:41:00", "9:53:00", "nebula", "hard", 0.7),
    ("Seagull Nebula", "7:04:00", "-10:27:00", "nebula", "medium", 2.0),
    ("Thor's Helmet", "7:18:30", "-13:13:00", "nebula", "hard", 0.6),
    ("M46 + M47", "7:41:46", "-14:48:36", "cluster", "easy", 0.5),
    ("M41 - Little Beehive", "6:46:00", "-20:46:00", "cluster", "easy", 0.6),
    # Taurus/Perseus
    ("M45 - Pleiades", "3:47:00", "24:07:00", "cluster", "easy", 1.8),
    ("Hyades", "4:27:00", "15:52:00", "cluster", "easy", 5.5),  # Too large for telephoto
    ("California Nebula", "4:03:18", "36:25:18", "nebula", "hard", 2.5),
    ("Double Cluster", "2:20:00", "57:08:00", "cluster", "easy", 1.0),
    ("M1 - Crab Nebula", "5:34:32", "22:00:52", "nebula", "medium", 0.2),
    # Winter galaxies
    ("NGC 2403", "7:36:51", "65:36:09", "galaxy", "medium", 0.4),

    # === SPRING (Mar-May evening) ===
    # Galaxy season!
    ("M81/M82 - Bode's Pair", "9:55:33", "69:03:55", "galaxy", "medium", 0.6),
    ("M51 - Whirlpool Galaxy", "13:29:52", "47:11:43", "galaxy", "medium", 0.2),
    ("M101 - Pinwheel Galaxy", "14:03:12", "54:20:57", "galaxy", "hard", 0.4),
    ("M63 - Sunflower Galaxy", "13:15:49", "42:01:45", "galaxy", "medium", 0.2),
    ("M106", "12:18:57", "47:18:14", "galaxy", "medium", 0.3),
    ("M94 - Cat's Eye Galaxy", "12:50:53", "41:07:14", "galaxy", "medium", 0.2),
    ("M64 - Black Eye Galaxy", "12:56:44", "21:40:58", "galaxy", "medium", 0.2),
    ("M104 - Sombrero Galaxy", "12:39:59", "-11:37:23", "galaxy", "medium", 0.15),
    ("M65/M66 - Leo Triplet", "11:18:56", "13:05:32", "galaxy", "medium", 0.7),
    ("NGC 2903", "9:32:10", "21:30:03", "galaxy", "medium", 0.2),
    ("NGC 4565 - Needle Galaxy", "12:36:21", "25:59:16", "galaxy", "medium", 0.3),
    ("NGC 4631 - Whale Galaxy", "12:42:08", "32:32:29", "galaxy", "medium", 0.3),
    ("M83 - Southern Pinwheel", "13:37:01", "-29:51:57", "galaxy", "medium", 0.2),
    ("Markarian's Chain", "12:27:00", "13:10:00", "galaxy", "medium", 1.5),
    ("NGC 5128 - Centaurus A", "13:25:28", "-43:01:09", "galaxy", "hard", 0.4),  # Low from FL but iconic
    # Spring clusters
    ("M44 - Beehive Cluster", "8:40:24", "19:40:00", "cluster", "easy", 1.5),
    ("M67 - Old Open Cluster", "8:51:18", "11:48:00", "cluster", "easy", 0.5),
    ("M3 - Globular", "13:42:11", "28:22:32", "cluster", "medium", 0.3),

    # === SUMMER (Jun-Aug evening) ===
    # Sagittarius/Scorpius (Milky Way core)
    ("M8 - Lagoon Nebula", "18:03:37", "-24:23:12", "nebula", "easy", 1.5),
    ("M20 - Trifid Nebula", "18:02:23", "-23:01:48", "nebula", "medium", 0.5),
    ("M17 - Omega Nebula", "18:20:26", "-16:10:36", "nebula", "easy", 0.4),
    ("M16 - Eagle Nebula", "18:18:48", "-13:47:00", "nebula", "medium", 0.6),
    ("M24 - Sagittarius Star Cloud", "18:16:54", "-18:33:00", "cluster", "easy", 1.7),
    ("Rho Ophiuchi Cloud", "16:25:35", "-23:26:50", "nebula", "hard", 4.0),
    ("Cat's Paw Nebula", "17:19:58", "-35:57:47", "nebula", "medium", 0.5),
    ("Pipe Nebula", "17:33:00", "-26:32:00", "nebula", "hard", 5.0),
    ("M6 - Butterfly Cluster", "17:40:00", "-32:15:00", "cluster", "easy", 0.4),
    ("M7 - Ptolemy Cluster", "17:53:51", "-34:47:34", "cluster", "easy", 1.3),
    ("M22 - Sagittarius Cluster", "18:36:24", "-23:54:17", "cluster", "easy", 0.5),
    # Cygnus/Lyra
    ("NGC 7000 - North America", "20:58:47", "44:19:48", "nebula", "medium", 2.0),
    ("IC 5070 - Pelican Nebula", "20:50:48", "44:21:00", "nebula", "medium", 1.0),
    ("Veil Nebula - East", "20:56:24", "31:42:30", "nebula", "medium", 1.2),
    ("Veil Nebula - West", "20:45:38", "30:42:30", "nebula", "medium", 1.2),
    ("Crescent Nebula", "20:12:06", "38:21:18", "nebula", "hard", 0.3),
    ("Sadr Region", "20:22:00", "40:15:00", "nebula", "medium", 2.0),
    ("M27 - Dumbbell Nebula", "19:59:36", "22:43:16", "nebula", "easy", 0.13),
    ("M57 - Ring Nebula", "18:53:35", "33:01:45", "nebula", "medium", 0.03),
    ("IC 1318 - Butterfly Nebula", "20:17:00", "41:41:00", "nebula", "medium", 1.5),
    ("NGC 6946 - Fireworks Galaxy", "20:34:52", "60:09:14", "galaxy", "hard", 0.2),
    # Serpens/Scutum
    ("Sh2-86 - Vulpecula OB", "19:40:00", "24:30:00", "nebula", "hard", 0.5),
    ("M11 - Wild Duck Cluster", "18:51:06", "-6:16:00", "cluster", "easy", 0.2),

    # === FALL (Sep-Nov evening) ===
    # Cassiopeia/Cepheus
    ("Heart Nebula", "2:32:42", "61:27:00", "nebula", "medium", 1.7),
    ("Soul Nebula", "2:51:30", "60:26:00", "nebula", "medium", 1.7),
    ("IC 1396 - Elephant Trunk", "21:39:06", "57:29:24", "nebula", "medium", 1.5),
    ("Bubble Nebula Region", "23:20:45", "61:12:42", "nebula", "hard", 0.3),
    ("Cave Nebula", "22:56:49", "62:27:08", "nebula", "hard", 0.7),
    ("Pacman Nebula", "1:29:00", "58:45:00", "nebula", "medium", 0.6),
    ("Iris Nebula", "21:01:36", "68:10:10", "nebula", "medium", 0.3),
    ("Wizard Nebula", "22:47:00", "58:06:00", "nebula", "medium", 0.6),
    ("NGC 7789 - Caroline's Rose", "23:57:24", "56:42:30", "cluster", "medium", 0.3),
    ("M52 - Scorpion Cluster", "23:24:48", "61:35:36", "cluster", "easy", 0.2),
    # Andromeda/Triangulum
    ("M31 - Andromeda Galaxy", "0:42:44", "41:16:09", "galaxy", "easy", 3.0),
    ("M33 - Triangulum Galaxy", "1:33:51", "30:39:37", "galaxy", "medium", 1.0),
    ("NGC 891 - Silver Sliver", "2:22:33", "42:20:57", "galaxy", "hard", 0.2),
    ("M77 + NGC 1055", "2:42:41", "-0:00:48", "galaxy", "medium", 0.12),
    # Aquarius/Pegasus/Sculptor
    ("NGC 253 - Sculptor Galaxy", "0:47:33", "-25:17:18", "galaxy", "medium", 0.5),
    ("Helix Nebula", "22:29:38", "-20:50:14", "nebula", "medium", 0.3),
    ("NGC 7331 + Stephan's Quintet", "22:37:04", "34:24:56", "galaxy", "hard", 0.3),

    # === YEAR-ROUND (globulars, always decent) ===
    ("M13 - Hercules Cluster", "16:41:41", "36:27:37", "cluster", "easy", 0.3),
    ("M92 - Hercules Globular", "17:17:07", "43:08:11", "cluster", "medium", 0.2),
    ("M5 - Rose Globular", "15:18:33", "2:04:58", "cluster", "medium", 0.4),
]


def _altitude_at(target: ephem.FixedBody, date) -> float:
    target.compute(make_observer(date))
    return to_deg(target.alt)


def _best_time_in_window(obs: ephem.Observer, target: ephem.FixedBody, night: dict):
    """Find when the target is highest within tonight's observing window."""
    transit = obs.next_transit(target, start=night["window_start"])
    if transit <= night["window_end"]:
        return ephem.Date(transit)
    # Transit falls outside the window: the target is either already setting
    # at the start of the window or still rising at the end. Take the better edge.
    if _altitude_at(target, night["window_start"]) >= _altitude_at(target, night["window_end"]):
        return night["window_start"]
    return night["window_end"]


def evaluate_target(name, ra, dec, obj_type, difficulty, size_deg, night) -> dict:
    """Compute a target's peak within the window and moon conditions at that time."""
    target = ephem.FixedBody()
    target._ra = ephem.hours(ra)
    target._dec = ephem.degrees(dec)

    obs = make_observer(night["window_start"])
    target.compute(obs)

    best_time = _best_time_in_window(obs, target, night)
    if best_time > night["prime_end"]:
        # A target already near peak height (and unblocked) at the prime
        # cutoff can be shot attended - only group it overnight if waiting
        # up past the cutoff actually buys real altitude
        peak_alt = _altitude_at(target, best_time)
        target.compute(make_observer(night["prime_end"]))
        prime_alt, prime_az = to_deg(target.alt), to_deg(target.az)
        if _shootable_by_cutoff(prime_alt, prime_az, peak_alt):
            best_time = night["prime_end"]
    obs_best = make_observer(best_time)
    target.compute(obs_best)
    altitude = to_deg(target.alt)

    # Moon conditions at the target's own peak time (the moon may rise or set
    # mid-window, so a single evening snapshot would be wrong for late peaks)
    moon = ephem.Moon(obs_best)
    moon_up = to_deg(moon.alt) > 0
    moon_sep = to_deg(ephem.separation(moon, target))

    is_late = best_time > night["prime_end"]
    hours_late = max(0.0, (best_time - night["prime_end"]) * 24)

    return {
        "name": name,
        "type": obj_type,
        "difficulty": difficulty,
        "altitude": round(altitude, 1),
        "azimuth": round(to_deg(target.az), 1),
        "visible": altitude > 15,
        "peak_time": fmt_time(best_time),
        "is_late": is_late,
        "hours_late": hours_late,
        "moon_up": moon_up,
        "moon_separation": round(moon_sep, 1),
        "moon_phase": moon.phase,
        "size_deg": size_deg,
    }


def _in_wedge(az: float, az_start: float, az_end: float) -> bool:
    if az_start <= az_end:
        return az_start <= az <= az_end
    return az >= az_start or az <= az_end  # wedge wraps through north


def is_blocked(altitude: float, azimuth: float, mask=None, min_altitude=None) -> bool:
    """True if the local horizon hides this sky position: below the global
    MIN_ALTITUDE floor, or inside a HORIZON_MASK wedge under its minimum."""
    mask = HORIZON_MASK if mask is None else mask
    floor = MIN_ALTITUDE if min_altitude is None else min_altitude
    if altitude < floor:
        return True
    return any(_in_wedge(azimuth, az_start, az_end) and altitude < min_alt
               for az_start, az_end, min_alt in mask)


def _shootable_by_cutoff(prime_alt: float, prime_az: float, peak_alt: float,
                         mask=None, min_altitude=None) -> bool:
    """True if a late-peaking target is close enough to its peak, and
    unblocked, at the prime cutoff to count as a before-midnight target."""
    return (prime_alt >= PRIME_USABLE_FRACTION * peak_alt
            and not is_blocked(prime_alt, prime_az, mask, min_altitude))


def score_target(t: dict) -> float:
    """Score a target 0-10 for tonight.

    Breakdown: 3.0 (altitude) + 3.5 (moon) + 1.5 (type) + 1.0 (difficulty)
             + 0.5 (FOV fit) + 0.5 (prime time) = 10.0
    """
    if not t["visible"]:
        return 0.0

    # Altitude (0-3.0): 30-75° optimal, continuous ramps below,
    # slight ding near zenith where the alt-az mount struggles
    alt = t["altitude"]
    if alt >= 75:
        alt_score = 2.5
    elif alt >= 30:
        alt_score = 3.0
    elif alt >= 20:
        alt_score = 1.0 + (alt - 20) * 0.2
    else:
        alt_score = 0.5 + (alt - 15) * 0.1

    # Moon (0-3.5), evaluated at the target's peak time
    if not t["moon_up"]:
        moon_score = 3.5  # Moon below horizon = perfect
    else:
        sep = t["moon_separation"]
        if sep >= 90:
            moon_score = 3.0
        elif sep >= 60:
            moon_score = 2.4
        elif sep >= 30:
            moon_score = 1.2
        else:
            moon_score = 0.5
        # Phase kicker: a dim moon (or a distant one) hurts much less
        phase = t["moon_phase"]
        if sep >= 60 or phase < 25:
            moon_score += 0.5
        elif phase < 50:
            moon_score += 0.35
        elif phase < 75:
            moon_score += 0.15

    # Type (0-1.5): galaxies favored, clusters mostly ignored
    type_score = TYPE_WEIGHTS.get(t["type"], 0.5)

    # Difficulty (0-1.0)
    diff_score = {"easy": 1.0, "medium": 0.8, "hard": 0.5}.get(t["difficulty"], 0.7)

    # FOV fit (0-0.5): how well the target fills DWARF3's frame
    fov_score = 0.0
    size = t["size_deg"]
    if size is not None:
        if DWARF3_OPTIMAL_TARGET_MIN <= size <= DWARF3_OPTIMAL_TARGET_MAX:
            fov_score = 0.5
        elif 0.1 <= size < DWARF3_OPTIMAL_TARGET_MIN:
            fov_score = 0.25
        elif DWARF3_OPTIMAL_TARGET_MAX < size <= 3.0:
            fov_score = 0.2
        # else: too large (>3°) or too tiny (<0.1°), no bonus

    # Prime time (0-0.5): full bonus for peaking before the cutoff,
    # gentle decay after — a great 2 AM target is still worth leaving out for
    prime_score = max(0.0, PRIME_BONUS - LATE_PENALTY_PER_HOUR * t["hours_late"])

    return round(alt_score + moon_score + type_score + diff_score + fov_score + prime_score, 1)


def get_recommendations(night: dict = None) -> list:
    """Get ranked list of targets for tonight (best first)."""
    night = night or get_night()

    targets = []
    for name, ra, dec, obj_type, difficulty, size_deg in DSO_CATALOG:
        t = evaluate_target(name, ra, dec, obj_type, difficulty, size_deg, night)
        # A target the local horizon blocks at its peak isn't a weak pick,
        # it's not a pick at all — drop it before any score filtering
        if is_blocked(t["altitude"], t["azimuth"]):
            continue
        t["score"] = score_target(t)
        targets.append(t)

    targets.sort(key=lambda x: x["score"], reverse=True)
    return targets


if __name__ == "__main__":
    night = get_night()
    print(f"=== Tonight's Targets ({fmt_time(night['window_start'])} - {fmt_time(night['window_end'])}, "
          f"prime until {fmt_time(night['prime_end'])}) ===\n")

    targets = get_recommendations(night)
    good = [t for t in targets if t["score"] >= MIN_TARGET_SCORE]

    if not good:
        print(f"No targets scoring {MIN_TARGET_SCORE}+ tonight. Best available:")
        good = [t for t in targets if t["visible"]][:5]

    for section, label in ((False, "PRIME (before cutoff)"), (True, "OVERNIGHT (leave it out)")):
        picks = [t for t in good if t["is_late"] == section]
        if not picks:
            continue
        print(f"--- {label} ---")
        for i, t in enumerate(picks[:10], 1):
            moon_note = f"moon {t['moon_separation']:.0f}° away" if t["moon_up"] else "moon down"
            print(f"{i:2}. {t['name']} [{t['score']}/10]")
            print(f"     {t['type']}, peak {t['peak_time']} @ {t['altitude']}°, {moon_note}")
        print()
