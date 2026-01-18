"""Deep sky object and planet target recommendations."""

import ephem
import math
import pytz
from datetime import datetime, timezone
from config import (
    LATITUDE, LONGITUDE, TIMEZONE, MAX_OBSERVING_HOUR,
    DWARF3_OPTIMAL_TARGET_MIN, DWARF3_OPTIMAL_TARGET_MAX
)

LOCAL_TZ = pytz.timezone(TIMEZONE)


def ephem_to_local(ephem_date) -> datetime:
    """Convert ephem date to local timezone datetime."""
    utc_dt = ephem.Date(ephem_date).datetime().replace(tzinfo=pytz.UTC)
    return utc_dt.astimezone(LOCAL_TZ)

# DWARF3-optimized catalog (150mm f/6.3, ~2.4° x 1.8° FOV)
# Organized by season (when best visible in evening)
# Scoring handles visibility - add lots, let the algorithm pick what's best tonight
# RA in hours:minutes, Dec in degrees:minutes
DSO_CATALOG = [
    # === WINTER (Dec-Feb evening) ===
    # Format: (name, RA, Dec, type, difficulty, size_degrees)
    # Size is optional - targets without size data won't get FOV bonus
    # Orion region
    ("M42 - Orion Nebula", "5:35:16", "-5:23:28", "nebula", "easy", 1.0),
    ("M43 - De Mairan's Nebula", "5:35:31", "-5:16:03", "nebula", "easy", 0.3),
    ("IC 434 - Horsehead Region", "5:40:59", "-2:27:30", "nebula", "hard", 1.0),
    ("Flame Nebula", "5:41:54", "-1:51:12", "nebula", "medium", 0.5),
    ("M78 - Reflection Nebula", "5:46:46", "0:03:50", "nebula", "medium", 0.3),
    ("Barnard's Loop", "5:27:00", "-3:58:00", "nebula", "hard", 10.0),  # Huge, needs wide field
    # Auriga/Gemini
    ("IC 405 - Flaming Star", "5:16:00", "34:21:00", "nebula", "medium", 0.5),
    ("IC 410 - Tadpole Nebula", "5:22:00", "33:24:00", "nebula", "medium", 0.5),
    ("IC 417 - Spider Nebula", "5:28:00", "34:25:00", "nebula", "medium", 0.4),
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

    # === SPRING (Mar-May evening) ===
    # Galaxy season - larger ones for DWARF3
    ("M81/M82 - Bode's Pair", "9:55:33", "69:03:55", "galaxy", "medium"),
    ("M51 - Whirlpool Galaxy", "13:29:52", "47:11:43", "galaxy", "medium"),
    ("M101 - Pinwheel Galaxy", "14:03:12", "54:20:57", "galaxy", "hard"),
    ("M63 - Sunflower Galaxy", "13:15:49", "42:01:45", "galaxy", "medium"),
    ("M106", "12:18:57", "47:18:14", "galaxy", "medium"),
    ("M94 - Cat's Eye Galaxy", "12:50:53", "41:07:14", "galaxy", "medium"),
    ("M64 - Black Eye Galaxy", "12:56:44", "21:40:58", "galaxy", "medium"),
    ("M104 - Sombrero Galaxy", "12:39:59", "-11:37:23", "galaxy", "medium"),
    ("M65/M66 - Leo Triplet", "11:18:56", "13:05:32", "galaxy", "medium"),
    ("NGC 2903", "9:32:10", "21:30:03", "galaxy", "medium"),
    # Spring clusters/nebulae
    ("M44 - Beehive Cluster", "8:40:24", "19:40:00", "cluster", "easy"),
    ("M67 - Old Open Cluster", "8:51:18", "11:48:00", "cluster", "easy"),
    ("M3 - Globular", "13:42:11", "28:22:32", "cluster", "medium"),

    # === SUMMER (Jun-Aug evening) ===
    # Sagittarius/Scorpius (Milky Way core)
    ("M8 - Lagoon Nebula", "18:03:37", "-24:23:12", "nebula", "easy"),
    ("M20 - Trifid Nebula", "18:02:23", "-23:01:48", "nebula", "medium"),
    ("M17 - Omega Nebula", "18:20:26", "-16:10:36", "nebula", "easy"),
    ("M16 - Eagle Nebula", "18:18:48", "-13:47:00", "nebula", "medium"),
    ("M24 - Sagittarius Star Cloud", "18:16:54", "-18:33:00", "cluster", "easy"),
    ("Rho Ophiuchi Cloud", "16:25:35", "-23:26:50", "nebula", "hard"),
    ("Cat's Paw Nebula", "17:19:58", "-35:57:47", "nebula", "medium"),
    ("Pipe Nebula", "17:33:00", "-26:32:00", "nebula", "hard"),
    ("M6 - Butterfly Cluster", "17:40:00", "-32:15:00", "cluster", "easy"),
    ("M7 - Ptolemy Cluster", "17:53:51", "-34:47:34", "cluster", "easy"),
    ("M22 - Sagittarius Cluster", "18:36:24", "-23:54:17", "cluster", "easy"),
    # Cygnus/Lyra
    ("NGC 7000 - North America", "20:58:47", "44:19:48", "nebula", "medium"),
    ("IC 5070 - Pelican Nebula", "20:50:48", "44:21:00", "nebula", "medium"),
    ("Veil Nebula - East", "20:56:24", "31:42:30", "nebula", "medium"),
    ("Veil Nebula - West", "20:45:38", "30:42:30", "nebula", "medium"),
    ("Crescent Nebula", "20:12:06", "38:21:18", "nebula", "hard"),
    ("Sadr Region", "20:22:00", "40:15:00", "nebula", "medium"),
    ("M27 - Dumbbell Nebula", "19:59:36", "22:43:16", "nebula", "easy"),
    ("M57 - Ring Nebula", "18:53:35", "33:01:45", "nebula", "medium"),
    ("IC 1318 - Butterfly Nebula", "20:17:00", "41:41:00", "nebula", "medium"),
    # Serpens/Scutum
    ("Sh2-86 - Vulpecula OB", "19:40:00", "24:30:00", "nebula", "hard"),
    ("M11 - Wild Duck Cluster", "18:51:06", "-6:16:00", "cluster", "easy"),

    # === FALL (Sep-Nov evening) ===
    # Cassiopeia/Cepheus
    ("Heart Nebula", "2:32:42", "61:27:00", "nebula", "medium"),
    ("Soul Nebula", "2:51:30", "60:26:00", "nebula", "medium"),
    ("IC 1396 - Elephant Trunk", "21:39:06", "57:29:24", "nebula", "medium"),
    ("Bubble Nebula Region", "23:20:45", "61:12:42", "nebula", "hard"),
    ("Cave Nebula", "22:56:49", "62:27:08", "nebula", "hard"),
    ("Pacman Nebula", "1:29:00", "58:45:00", "nebula", "medium"),
    ("NGC 7789 - Caroline's Rose", "23:57:24", "56:42:30", "cluster", "medium"),
    ("M52 - Scorpion Cluster", "23:24:48", "61:35:36", "cluster", "easy"),
    # Andromeda/Triangulum
    ("M31 - Andromeda Galaxy", "0:42:44", "41:16:09", "galaxy", "easy"),
    ("M33 - Triangulum Galaxy", "1:33:51", "30:39:37", "galaxy", "medium"),
    # Aquarius/Pegasus
    ("NGC 253 - Sculptor Galaxy", "0:47:33", "-25:17:18", "galaxy", "medium"),
    ("Helix Nebula", "22:29:38", "-20:50:14", "nebula", "medium"),
    ("NGC 7331 + Stephan's Quintet", "22:37:04", "34:24:56", "galaxy", "hard"),

    # === YEAR-ROUND (circumpolar or always visible) ===
    ("M13 - Hercules Cluster", "16:41:41", "36:27:37", "cluster", "easy"),
    ("M92 - Hercules Globular", "17:17:07", "43:08:11", "cluster", "medium"),
    ("M5 - Rose Globular", "15:18:33", "2:04:58", "cluster", "medium"),
]


def get_observer_tonight() -> ephem.Observer:
    """Create an observer for tonight's prime viewing time (2 hrs after sunset)."""
    obs = ephem.Observer()
    obs.lat = str(LATITUDE)
    obs.lon = str(LONGITUDE)
    obs.date = datetime.now(timezone.utc)

    # Get next sunset
    sun = ephem.Sun()
    try:
        next_sunset = obs.next_setting(sun)
    except ephem.AlwaysUpError:
        next_sunset = obs.date

    # Set time to 2 hours after sunset (astronomical darkness)
    obs.date = ephem.Date(next_sunset + 2 * ephem.hour)
    return obs


def angular_separation(ra1, dec1, ra2, dec2) -> float:
    """Calculate angular separation in degrees between two points."""
    # Convert to radians
    d1 = math.radians(dec1)
    d2 = math.radians(dec2)
    ra_diff = math.radians((ra1 - ra2) * 15)  # RA in hours to degrees to radians

    cos_sep = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(ra_diff)
    cos_sep = max(-1, min(1, cos_sep))  # Clamp for numerical stability
    return math.degrees(math.acos(cos_sep))


def get_target_info(obs: ephem.Observer, name: str, ra: str, dec: str,
                    obj_type: str, difficulty: str, moon: ephem.Moon,
                    window_end: ephem.Date, size_deg: float = None) -> dict:
    """Calculate visibility info for a target.

    Scores target based on its BEST altitude within the observing window,
    not just at the snapshot time (2hrs after sunset).

    Args:
        size_deg: Optional apparent size in degrees for FOV fit scoring
    """
    target = ephem.FixedBody()
    target._ra = ephem.hours(ra)
    target._dec = ephem.degrees(dec)
    target.compute(obs)

    # Current altitude at obs.date (2hrs after sunset)
    altitude_now = float(target.alt) * 180 / math.pi
    azimuth = float(target.az) * 180 / math.pi

    # Moon separation (at current time)
    moon_ra = float(moon.ra) * 12 / math.pi  # radians to hours
    moon_dec = float(moon.dec) * 180 / math.pi
    target_ra = float(target.ra) * 12 / math.pi
    target_dec = float(target.dec) * 180 / math.pi
    moon_sep = angular_separation(target_ra, target_dec, moon_ra, moon_dec)

    # Calculate transit time (when target is highest)
    try:
        transit = obs.next_transit(target)
        transit_time = ephem_to_local(transit).strftime("%-I:%M %p")

        # Determine best altitude within observing window
        window_start = obs.date
        if window_start <= transit <= window_end:
            # Transit is within window - use peak altitude
            obs_at_best = obs.copy()
            obs_at_best.date = transit
            target.compute(obs_at_best)
            best_altitude = float(target.alt) * 180 / math.pi
        elif transit < window_start:
            # Transit already passed - target is setting, use current altitude
            best_altitude = altitude_now
        else:
            # Transit is after window ends - target is rising, use altitude at window end
            obs_at_best = obs.copy()
            obs_at_best.date = window_end
            target.compute(obs_at_best)
            best_altitude = float(target.alt) * 180 / math.pi
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        transit_time = "N/A"
        best_altitude = altitude_now

    return {
        "name": name,
        "type": obj_type,
        "difficulty": difficulty,
        "altitude": round(best_altitude, 1),  # Use BEST altitude for scoring
        "azimuth": round(azimuth, 1),
        "moon_separation": round(moon_sep, 1),
        "visible": best_altitude > 15,  # Visible if it gets above 15° during window
        "transit_time": transit_time,
        "size_deg": size_deg,  # Apparent size in degrees (None if not specified)
    }


def get_planets(obs: ephem.Observer, moon: ephem.Moon) -> list:
    """Get planet positions."""
    planets = [
        ("Venus", ephem.Venus(obs)),
        ("Mars", ephem.Mars(obs)),
        ("Jupiter", ephem.Jupiter(obs)),
        ("Saturn", ephem.Saturn(obs)),
    ]

    results = []
    for name, planet in planets:
        altitude = float(planet.alt) * 180 / math.pi
        azimuth = float(planet.az) * 180 / math.pi

        moon_ra = float(moon.ra) * 12 / math.pi
        moon_dec = float(moon.dec) * 180 / math.pi
        planet_ra = float(planet.ra) * 12 / math.pi
        planet_dec = float(planet.dec) * 180 / math.pi
        moon_sep = angular_separation(planet_ra, planet_dec, moon_ra, moon_dec)

        results.append({
            "name": name,
            "type": "planet",
            "difficulty": "easy",
            "altitude": round(altitude, 1),
            "azimuth": round(azimuth, 1),
            "moon_separation": round(moon_sep, 1),
            "visible": altitude > 10,
        })

    return results


def get_recommendations() -> list:
    """Get ranked list of targets for tonight.

    Returns:
        List of targets sorted by score (best first)
    """
    obs = get_observer_tonight()
    moon = ephem.Moon(obs)
    moon_phase = moon.phase

    # Calculate observing window end time (min of 11 PM, moon rise if >50%, or dawn)
    window_start_dt = ephem_to_local(obs.date)
    max_obs_time = window_start_dt.replace(hour=MAX_OBSERVING_HOUR, minute=0, second=0, microsecond=0)
    if max_obs_time < window_start_dt:
        max_obs_time = max_obs_time.replace(day=max_obs_time.day + 1)
    max_obs_ephem = ephem.Date(max_obs_time.astimezone(pytz.UTC))

    sun = ephem.Sun()
    obs_now = ephem.Observer()
    obs_now.lat = str(LATITUDE)
    obs_now.lon = str(LONGITUDE)
    obs_now.date = datetime.now(timezone.utc)
    sunrise = obs_now.next_rising(sun)

    end_times = []
    moon_rise_time = None
    try:
        moon_rise_time = obs.next_rising(moon)
        if moon_phase > 50 and moon_rise_time < sunrise:
            end_times.append(moon_rise_time)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        pass
    end_times.append(ephem.Date(sunrise - 1 * ephem.hour))
    end_times.append(max_obs_ephem)
    window_end = min(end_times)

    targets = []

    # Add DSOs (planets skipped - too small for DWARF3's wide field)
    for entry in DSO_CATALOG:
        # Handle both 5-tuple (without size) and 6-tuple (with size) catalog entries
        if len(entry) == 5:
            name, ra, dec, obj_type, difficulty = entry
            size_deg = None
        else:
            name, ra, dec, obj_type, difficulty, size_deg = entry

        info = get_target_info(obs, name, ra, dec, obj_type, difficulty, moon, window_end, size_deg)
        targets.append(info)

    # Get moon altitude to check if it's actually visible
    moon_alt_deg = float(moon.alt) * 180 / math.pi
    moon_is_up = moon_alt_deg > 0

    # Score each target on 1-10 scale
    for t in targets:
        if not t["visible"]:
            t["score"] = 0
            continue

        # Altitude score (0-3 points): smooth gradient, 30-70° optimal
        alt = t["altitude"]
        if alt >= 70:
            alt_score = 2.5  # High altitude, more atmosphere near horizon
        elif alt >= 30:
            alt_score = 3.0  # Optimal range
        elif alt >= 20:
            # Smooth gradient from 2.0 at 30° down to 1.0 at 20°
            alt_score = 1.0 + (alt - 20) * 0.1
        elif alt >= 15:
            # Smooth gradient from 1.0 at 20° down to 0.5 at 15°
            alt_score = 0.5 + (alt - 15) * 0.1
        else:
            alt_score = 0

        # Moon separation & phase scoring (max 3.0 + 1.5 = 4.5 points)
        # CRITICAL: Only apply moon penalties if moon is actually above horizon
        if not moon_is_up:
            # Moon is down - perfect conditions for DSO
            moon_sep_score = 3.0
            moon_phase_score = 1.5
        else:
            # Moon is up - apply separation and phase penalties
            sep = t["moon_separation"]
            if sep >= 90:
                moon_sep_score = 3.0
            elif sep >= 60:
                moon_sep_score = 2.0
            elif sep >= 30:
                moon_sep_score = 1.0
            else:
                moon_sep_score = 0.5

            # Moon phase score (0-1.5 points): only penalize if moon is close (<60°)
            # If moon is far away, phase doesn't matter
            if sep >= 60:
                moon_phase_score = 1.5  # Moon far enough to not matter
            else:
                # Moon is close, so phase matters
                if moon_phase < 25:
                    moon_phase_score = 1.5
                elif moon_phase < 50:
                    moon_phase_score = 1.1
                elif moon_phase < 75:
                    moon_phase_score = 0.8
                else:
                    moon_phase_score = 0.4

        # Difficulty score (0-1.5 points): easier = higher
        diff_scores = {"easy": 1.5, "medium": 1.1, "hard": 0.8}
        diff_score = diff_scores.get(t["difficulty"], 1.0)

        # Object type bonus (0-0.5 points): preference for galaxies
        type_bonus = 0.0
        if t["type"] == "galaxy":
            type_bonus = 0.5
        elif t["type"] == "nebula":
            type_bonus = 0.2
        # clusters get 0

        # FOV fit bonus (0-0.5 points): targets that fit DWARF3's FOV well
        fov_bonus = 0.0
        if t["size_deg"] is not None:
            size = t["size_deg"]
            if DWARF3_OPTIMAL_TARGET_MIN <= size <= DWARF3_OPTIMAL_TARGET_MAX:
                # Optimal size for DWARF3's 3° x 1.65° FOV
                fov_bonus = 0.5
            elif size < DWARF3_OPTIMAL_TARGET_MIN and size >= 0.1:
                # Small but visible, proportional bonus
                fov_bonus = 0.25
            elif size > DWARF3_OPTIMAL_TARGET_MAX and size <= 3.0:
                # Slightly too large but still workable
                fov_bonus = 0.2
            # else: too large (>3°) or too tiny (<0.1°), no bonus

        # Total: max 10 points
        # Breakdown: 3.0 (alt) + 3.0 (moon_sep) + 1.5 (moon_phase) + 1.5 (diff) + 0.5 (type) + 0.5 (fov) = 10.0
        total = alt_score + moon_sep_score + moon_phase_score + diff_score + type_bonus + fov_bonus
        t["score"] = round(total, 1)

    # Sort by score descending
    targets.sort(key=lambda x: x["score"], reverse=True)

    return targets


if __name__ == "__main__":
    obs = get_observer_tonight()
    viewing_time = ephem_to_local(obs.date).strftime("%-I:%M %p")
    print(f"=== Tonight's Top Targets (calculated for {viewing_time}) ===\n")

    targets = get_recommendations()

    # Filter to 6+ and take top 5
    good_targets = [t for t in targets if t["score"] >= 6][:5]

    if not good_targets:
        print("No targets scoring 6+ right now")
        print("\nBest available:")
        for t in targets[:3]:
            if t["visible"]:
                print(f"  {t['name']} - Score: {t['score']}/10")
    else:
        for i, t in enumerate(good_targets, 1):
            print(f"{i}. {t['name']} [{t['score']}/10]")
            print(f"   Alt: {t['altitude']}° | Moon sep: {t['moon_separation']}°")
            print()
