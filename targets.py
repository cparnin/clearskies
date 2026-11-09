"""Deep sky object target recommendations, scored for tonight's window."""

import ephem

from astro import fmt_time, get_night, make_observer, to_deg
from config import (
    DWARF3_OPTIMAL_TARGET_MAX, DWARF3_OPTIMAL_TARGET_MIN, HORIZON_MASK,
    LATE_PENALTY_PER_HOUR, MIN_ALTITUDE, MIN_TARGET_SCORE, TARGET_TYPES, TYPE_WEIGHTS,
)

PRIME_BONUS = 0.5  # points available for peaking before the prime cutoff
PRIME_USABLE_FRACTION = 0.8  # at the cutoff, this fraction of peak altitude counts as "already there"
SAMPLE_MINUTES = 10  # resolution of each target's track across the night

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
    ("NGC 4631 + NGC 4656 - Whale & Hockey Stick", "12:43:03", "32:21:17", "galaxy", "medium", 0.6),  # both in one frame
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

    # === ODD & INTERACTING GALAXIES (coordinates from NED) ===
    # Collisions, polar rings, warps, dust lanes, and whole galaxy clusters -
    # also fills the summer gap in the galaxy list
    ("NGC 4038/4039 - Antennae Galaxies", "12:01:53", "-18:52:37", "galaxy", "hard", 0.12),
    ("NGC 4490 - Cocoon Galaxy", "12:30:36", "41:38:38", "galaxy", "medium", 0.15),
    ("NGC 4449 - Box Galaxy", "12:28:11", "44:05:37", "galaxy", "medium", 0.1),
    ("NGC 4567/4568 - Siamese Twins", "12:36:34", "11:14:55", "galaxy", "hard", 0.08),
    ("NGC 3718 - Warped Galaxy", "11:32:35", "53:04:05", "galaxy", "hard", 0.14),
    ("NGC 2685 - Helix Galaxy", "8:55:35", "58:44:04", "galaxy", "hard", 0.08),  # polar ring
    ("Coma Galaxy Cluster", "12:59:49", "27:58:52", "galaxy", "hard", 1.0),
    ("NGC 5907 - Splinter Galaxy", "15:15:53", "56:19:48", "galaxy", "medium", 0.21),
    ("NGC 5866 - Spindle Galaxy", "15:06:30", "55:45:48", "galaxy", "medium", 0.11),
    ("Draco Trio", "15:38:44", "59:21:36", "galaxy", "hard", 0.4),  # NGC 5981/5982/5985
    ("Hercules Galaxy Cluster", "16:05:15", "17:44:35", "galaxy", "hard", 0.5),
    ("NGC 6503 - Lost-in-Space Galaxy", "17:49:26", "70:08:40", "galaxy", "medium", 0.12),
    ("NGC 7814 - Little Sombrero", "0:03:15", "16:08:43", "galaxy", "medium", 0.09),
    ("NGC 660 - Polar Ring Galaxy", "1:43:02", "13:38:42", "galaxy", "hard", 0.15),
    ("Perseus Galaxy Cluster", "3:19:49", "41:30:42", "galaxy", "hard", 0.8),
    ("IC 342 - Hidden Galaxy", "3:46:49", "68:05:47", "galaxy", "hard", 0.35),
    ("NGC 2146 - Dusty Hand Galaxy", "6:18:38", "78:21:25", "galaxy", "medium", 0.1),
    ("NGC 2207 - Colliding Pair", "6:16:22", "-21:22:22", "galaxy", "hard", 0.07),

    # === YEAR-ROUND (globulars, always decent) ===
    ("M13 - Hercules Cluster", "16:41:41", "36:27:37", "cluster", "easy", 0.3),
    ("M92 - Hercules Globular", "17:17:07", "43:08:11", "cluster", "medium", 0.2),
    ("M5 - Rose Globular", "15:18:33", "2:04:58", "cluster", "medium", 0.4),
]


# Bucket-list nebulae that score at full galaxy weight instead of the
# ordinary-nebula weight. Everything else nebulous ranks a point lower, so the
# list stays galaxy-heavy without ever hiding the icons. Names must match
# DSO_CATALOG exactly.
SHOWPIECES = {
    "M42 - Orion Nebula",
    "IC 434 - Horsehead Region",
    "Rosette Nebula",
    "M8 - Lagoon Nebula",
    "M20 - Trifid Nebula",
    "M16 - Eagle Nebula",
    "Veil Nebula - East",
    "Veil Nebula - West",
    "NGC 7000 - North America",
    "Heart Nebula",
    "Soul Nebula",
    "Helix Nebula",
}


def _sky_track(target: ephem.FixedBody, night: dict) -> list:
    """(time, alt, az) samples across the window: every SAMPLE_MINUTES, plus
    the window edges, the prime cutoff, and the exact transit when it falls
    inside the window, so neither the true peak nor the cutoff is missed."""
    start, end = night["window_start"], night["window_end"]
    times = {float(start), float(end), float(night["prime_end"])}
    step = SAMPLE_MINUTES * ephem.minute
    t = start + step
    while t < end:
        times.add(float(t))
        t += step
    transit = make_observer(start).next_transit(target, start=start)
    if transit <= end:
        times.add(float(transit))

    track = []
    for t in sorted(times):
        target.compute(make_observer(ephem.Date(t)))
        track.append((ephem.Date(t), to_deg(target.alt), to_deg(target.az)))
    return track


def best_moment(track: list, prime_end, mask=None, min_altitude=None):
    """When to shoot: the highest point of the track the local horizon
    doesn't block, as a (time, alt, az) sample - or None if the target never
    clears the horizon tonight.

    Scoring the visible sky, not the meridian peak, matters for a partial
    horizon: with only the east open, a target that transits due south is
    shot on its climb, not dropped for peaking in the blocked half.

    If the best moment lands after the prime cutoff but the target is already
    within PRIME_USABLE_FRACTION of that altitude (and unblocked) by the
    cutoff, the highest pre-cutoff moment wins instead - the overnight tag is
    only for targets where leaving the scope out buys real altitude.
    """
    usable = [s for s in track if not is_blocked(s[1], s[2], mask, min_altitude)]
    if not usable:
        return None
    best = max(usable, key=lambda s: s[1])
    if best[0] > prime_end:
        early = [s for s in usable if s[0] <= prime_end]
        if early:
            by_cutoff = max(early, key=lambda s: s[1])
            if by_cutoff[1] >= PRIME_USABLE_FRACTION * best[1]:
                best = by_cutoff
    return best


def evaluate_target(name, ra, dec, obj_type, difficulty, size_deg, night) -> dict | None:
    """Find a target's best moment in tonight's visible sky and the moon
    conditions at that moment. None if the local horizon hides it all night."""
    target = ephem.FixedBody()
    target._ra = ephem.hours(ra)
    target._dec = ephem.degrees(dec)

    moment = best_moment(_sky_track(target, night), night["prime_end"])
    if moment is None:
        return None
    best_time, altitude, azimuth = moment

    # Moon conditions at the target's own best time (the moon may rise or set
    # mid-window, so a single evening snapshot would be wrong for late peaks)
    obs_best = make_observer(best_time)
    target.compute(obs_best)
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
        "azimuth": round(azimuth, 1) % 360,
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
    az %= 360  # radian round-off can hand back 360.00001 for due north
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

    # Moon (0-3.5), evaluated at the target's peak time. Phase dominates:
    # a bright moon washes out the whole sky for broadband imaging, so
    # separation only softens the blow — it can't rescue a full-moon night.
    if not t["moon_up"]:
        moon_score = 3.5  # Moon below horizon = perfect
    else:
        phase, sep = t["moon_phase"], t["moon_separation"]
        if phase >= 75:
            moon_score = 0.4
        elif phase >= 50:
            moon_score = 1.2
        elif phase >= 25:
            moon_score = 2.0
        else:
            moon_score = 2.8
        if sep >= 90:
            moon_score += 0.7
        elif sep >= 60:
            moon_score += 0.4
        elif sep < 30:
            moon_score -= 0.4
        moon_score = max(0.0, min(3.5, moon_score))

    # Type (0-1.5): galaxies favored, clusters mostly ignored; showpiece
    # nebulae are promoted to galaxy weight so the icons stay in the running
    type_score = TYPE_WEIGHTS.get(t["type"], 0.5)
    if t["name"] in SHOWPIECES:
        type_score = max(type_score, TYPE_WEIGHTS["galaxy"])

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


def get_recommendations(night: dict = None, types=None) -> list:
    """Get ranked list of targets for tonight (best first), limited to
    `types` (default: TARGET_TYPES from config)."""
    night = night or get_night()
    types = TARGET_TYPES if types is None else types

    targets = []
    for name, ra, dec, obj_type, difficulty, size_deg in DSO_CATALOG:
        if obj_type not in types:
            continue
        t = evaluate_target(name, ra, dec, obj_type, difficulty, size_deg, night)
        # A target the local horizon hides all night isn't a weak pick,
        # it's not a pick at all — drop it before any score filtering
        if t is None:
            continue
        t["score"] = score_target(t)
        targets.append(t)

    # Ties go to the galaxy - a showpiece nebula matches galaxy weight but
    # shouldn't push an equal-scoring galaxy out of the notification's top 3
    targets.sort(key=lambda x: (x["score"], x["type"] == "galaxy"), reverse=True)
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

    for i, t in enumerate(good[:10], 1):
        moon_note = f"moon {t['moon_separation']:.0f}° away" if t["moon_up"] else "moon down"
        late_note = " (overnight)" if t["is_late"] else ""
        print(f"{i:2}. {t['name']} [{t['score']}/10]{late_note}")
        print(f"     {t['type']}, best {t['peak_time']} @ {t['altitude']}° az {t['azimuth']:.0f}°, {moon_note}")
