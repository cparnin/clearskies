"""Deep sky object and planet target recommendations."""

import ephem
import math
from datetime import datetime, timezone
from config import LATITUDE, LONGITUDE

# DWARF3-optimized catalog (150mm f/6.3, ~2.4° x 1.8° FOV)
# Best for: large nebulae, big galaxies, open clusters
# RA in hours:minutes, Dec in degrees:minutes
DSO_CATALOG = [
    # Large Nebulae (excellent for DWARF3)
    ("M42 - Orion Nebula", "5:35:16", "-5:23:28", "nebula", "easy"),
    ("M8 - Lagoon Nebula", "18:03:37", "-24:23:12", "nebula", "easy"),
    ("M20 - Trifid Nebula", "18:02:23", "-23:01:48", "nebula", "medium"),
    ("M17 - Omega Nebula", "18:20:26", "-16:10:36", "nebula", "easy"),
    ("M27 - Dumbbell Nebula", "19:59:36", "22:43:16", "nebula", "easy"),
    ("NGC 7000 - North America", "20:58:47", "44:19:48", "nebula", "medium"),
    ("IC 5070 - Pelican Nebula", "20:50:48", "44:21:00", "nebula", "medium"),
    ("M16 - Eagle Nebula", "18:18:48", "-13:47:00", "nebula", "medium"),
    ("IC 1396 - Elephant Trunk", "21:39:06", "57:29:24", "nebula", "medium"),
    ("Rosette Nebula", "6:33:45", "4:59:54", "nebula", "medium"),
    ("M43 - De Mairan's Nebula", "5:35:31", "-5:16:03", "nebula", "easy"),
    ("IC 434 - Horsehead Region", "5:40:59", "-2:27:30", "nebula", "hard"),
    ("California Nebula", "4:03:18", "36:25:18", "nebula", "hard"),
    ("Soul Nebula", "2:51:30", "60:26:00", "nebula", "medium"),
    ("Heart Nebula", "2:32:42", "61:27:00", "nebula", "medium"),

    # Large Galaxies (good for DWARF3 wide field)
    ("M31 - Andromeda Galaxy", "0:42:44", "41:16:09", "galaxy", "easy"),
    ("M33 - Triangulum Galaxy", "1:33:51", "30:39:37", "galaxy", "medium"),
    ("M81/M82 - Bode's Pair", "9:55:33", "69:03:55", "galaxy", "medium"),
    ("NGC 253 - Sculptor Galaxy", "0:47:33", "-25:17:18", "galaxy", "medium"),
    ("Large Magellanic Cloud", "5:23:34", "-69:45:22", "galaxy", "easy"),

    # Open Clusters (perfect for wide field)
    ("M45 - Pleiades", "3:47:00", "24:07:00", "cluster", "easy"),
    ("M44 - Beehive Cluster", "8:40:24", "19:40:00", "cluster", "easy"),
    ("Double Cluster", "2:20:00", "57:08:00", "cluster", "easy"),
    ("M35 - Gemini Cluster", "6:09:00", "24:21:00", "cluster", "easy"),
    ("M46 + M47", "7:41:46", "-14:48:36", "cluster", "easy"),
    ("Hyades", "4:27:00", "15:52:00", "cluster", "easy"),
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
                    obj_type: str, difficulty: str, moon: ephem.Moon) -> dict:
    """Calculate visibility info for a target."""
    target = ephem.FixedBody()
    target._ra = ephem.hours(ra)
    target._dec = ephem.degrees(dec)
    target.compute(obs)

    altitude = float(target.alt) * 180 / math.pi
    azimuth = float(target.az) * 180 / math.pi

    # Moon separation
    moon_ra = float(moon.ra) * 12 / math.pi  # radians to hours
    moon_dec = float(moon.dec) * 180 / math.pi
    target_ra = float(target.ra) * 12 / math.pi
    target_dec = float(target.dec) * 180 / math.pi
    moon_sep = angular_separation(target_ra, target_dec, moon_ra, moon_dec)

    return {
        "name": name,
        "type": obj_type,
        "difficulty": difficulty,
        "altitude": round(altitude, 1),
        "azimuth": round(azimuth, 1),
        "moon_separation": round(moon_sep, 1),
        "visible": altitude > 15,  # Above 15° for decent viewing
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

    targets = []

    # Add DSOs (planets skipped - too small for DWARF3's wide field)
    for name, ra, dec, obj_type, difficulty in DSO_CATALOG:
        info = get_target_info(obs, name, ra, dec, obj_type, difficulty, moon)
        targets.append(info)

    # Score each target on 1-10 scale
    for t in targets:
        if not t["visible"]:
            t["score"] = 0
            continue

        # Altitude score (0-3 points): 30-70° is optimal
        alt = t["altitude"]
        if alt >= 30 and alt <= 70:
            alt_score = 3.0
        elif alt >= 20 and alt < 30:
            alt_score = 2.0
        elif alt > 70:
            alt_score = 2.5  # High is okay, just more atmosphere at horizon
        else:
            alt_score = 1.0

        # Moon separation score (0-3 points): farther is better
        sep = t["moon_separation"]
        if sep >= 90:
            moon_sep_score = 3.0
        elif sep >= 60:
            moon_sep_score = 2.0
        elif sep >= 30:
            moon_sep_score = 1.0
        else:
            moon_sep_score = 0.5

        # Moon phase penalty (0-2 points): darker is better
        if moon_phase < 25:
            moon_phase_score = 2.0
        elif moon_phase < 50:
            moon_phase_score = 1.5
        elif moon_phase < 75:
            moon_phase_score = 1.0
        else:
            moon_phase_score = 0.5

        # Difficulty score (0-2 points): easier = higher
        diff_scores = {"easy": 2.0, "medium": 1.5, "hard": 1.0}
        diff_score = diff_scores.get(t["difficulty"], 1.0)

        # Total: max 10 points
        total = alt_score + moon_sep_score + moon_phase_score + diff_score
        t["score"] = round(total, 1)

    # Sort by score descending
    targets.sort(key=lambda x: x["score"], reverse=True)

    return targets


if __name__ == "__main__":
    obs = get_observer_tonight()
    viewing_time = ephem.localtime(obs.date).strftime("%-I:%M %p")
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
