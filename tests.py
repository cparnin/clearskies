"""Offline sanity tests - no network needed. Run: python tests.py"""

from datetime import datetime, timedelta

from astro import LOCAL_TZ, get_night, local_to_ephem
from config import _parse_horizon_mask
from main import assess_conditions, display_name, effective_night, find_clear_stretch
from targets import DSO_CATALOG, SHOWPIECES, _shootable_by_cutoff, is_blocked, score_target

passed = 0


def check(label, condition, detail=""):
    global passed
    assert condition, f"FAIL: {label} {detail}"
    passed += 1
    print(f"  ok - {label}")


base = LOCAL_TZ.localize(datetime(2026, 1, 15, 20, 0))  # window math must survive any date


def fake_hours(clouds, start=base):
    return [{"time": start + timedelta(hours=i), "label": (start + timedelta(hours=i)).strftime("%-I %p"),
             "cloud_cover": c, "humidity": 60, "wind_mph": 4, "temperature_f": 60, "visibility_mi": 15}
            for i, c in enumerate(clouds)]


def fake_target(**overrides):
    t = {"name": "Test Target", "visible": True, "altitude": 50.0, "moon_up": False,
         "moon_separation": 120.0, "moon_phase": 0.0, "type": "galaxy", "difficulty": "easy",
         "size_deg": 1.0, "hours_late": 0.0}
    t.update(overrides)
    return t


print("catalog:")
check("all entries are 6-tuples", all(len(e) == 6 for e in DSO_CATALOG))
check("known types only", {e[3] for e in DSO_CATALOG} == {"nebula", "galaxy", "cluster"})
check("known difficulties only", {e[4] for e in DSO_CATALOG} <= {"easy", "medium", "hard"})
check("no duplicate names", len({e[0] for e in DSO_CATALOG}) == len(DSO_CATALOG))
check("showpieces all exist in catalog", SHOWPIECES <= {e[0] for e in DSO_CATALOG})

print("scoring:")
check("perfect galaxy scores 10", score_target(fake_target()) == 10.0)
check("cluster penalized vs galaxy", score_target(fake_target(type="cluster")) == 8.7)
check("ordinary nebula a point behind galaxy", score_target(fake_target(type="nebula")) == 9.0)
check("showpiece nebula scores at galaxy weight",
      score_target(fake_target(name="M42 - Orion Nebula", type="nebula")) == 10.0)
check("late peak decays", score_target(fake_target(hours_late=2.0)) == 9.7)
check("very late loses full prime bonus", score_target(fake_target(hours_late=8.0)) == 9.5)
check("full moon nearby is heavily penalized",
      score_target(fake_target(moon_up=True, moon_separation=25.0, moon_phase=95.0)) == 6.5)
check("separation can't rescue a full moon",
      score_target(fake_target(moon_up=True, moon_separation=120.0, moon_phase=95.0)) <= 7.6)
check("crescent moon far away barely hurts",
      score_target(fake_target(moon_up=True, moon_separation=120.0, moon_phase=15.0)) == 10.0)
check("moon down beats bright moon nearby",
      score_target(fake_target()) > score_target(fake_target(moon_up=True, moon_separation=25.0, moon_phase=95.0)))
check("invisible target scores 0", score_target(fake_target(visible=False)) == 0.0)
check("low altitude hurts", score_target(fake_target(altitude=18.0)) < score_target(fake_target(altitude=45.0)))

print("horizon mask:")
check("clear horizon blocks nothing", not is_blocked(20.0, 300.0, mask=[], min_altitude=15.0))
check("global floor blocks low peaks", is_blocked(29.5, 100.0, mask=[], min_altitude=30.0))
check("wedge blocks under its min alt", is_blocked(45.0, 293.0, mask=[(250, 340, 90)], min_altitude=0.0))
check("target above wedge clears it", not is_blocked(50.0, 300.0, mask=[(250, 340, 45)], min_altitude=0.0))
check("azimuth outside wedge unaffected", not is_blocked(20.0, 180.0, mask=[(250, 340, 90)], min_altitude=15.0))
check("wedge edges are inclusive", is_blocked(30.0, 250.0, mask=[(250, 340, 90)], min_altitude=0.0)
      and is_blocked(30.0, 340.0, mask=[(250, 340, 90)], min_altitude=0.0))
check("wraparound wedge blocks across north",
      is_blocked(30.0, 5.0, mask=[(340, 20, 35)], min_altitude=0.0)
      and is_blocked(30.0, 350.0, mask=[(340, 20, 35)], min_altitude=0.0))
check("wraparound wedge spares the south", not is_blocked(30.0, 180.0, mask=[(340, 20, 35)], min_altitude=0.0))
check("env mask parsing",
      _parse_horizon_mask("250-340:90,340-20:35") == [(250.0, 340.0, 90.0), (340.0, 20.0, 35.0)])

print("prime cutoff:")
check("near-peak by cutoff counts as prime",  # Veil East on 8/11: 76° at midnight, 86° peak at 1 AM
      _shootable_by_cutoff(76.0, 12.0, 86.4, mask=[], min_altitude=30.0))
check("still climbing stays overnight", not _shootable_by_cutoff(40.0, 90.0, 80.0, mask=[], min_altitude=30.0))
check("blocked at cutoff stays overnight",
      not _shootable_by_cutoff(50.0, 300.0, 55.0, mask=[(250, 340, 90)], min_altitude=30.0))
check("below floor at cutoff stays overnight",
      not _shootable_by_cutoff(25.0, 90.0, 28.0, mask=[], min_altitude=30.0))

print("display names:")
check("catalog prefix dropped", display_name("M8 - Lagoon Nebula") == "Lagoon Nebula")
check("NGC prefix dropped", display_name("NGC 2174 - Monkey Head") == "Monkey Head")
check("descriptive suffix kept", display_name("Veil Nebula - East") == "Veil Nebula - East")
check("bare designations kept", display_name("M77 + NGC 1055") == "M77 + NGC 1055")
check("plain name unchanged", display_name("Iris Nebula") == "Iris Nebula")

print("clear stretch:")
check("finds the clear run", [h["cloud_cover"] for h in find_clear_stretch(fake_hours([90, 10, 5, 10, 95]))] == [10, 5, 10])
check("no stretch when socked in", find_clear_stretch(fake_hours([100] * 6)) is None)
check("single clear hour is not a stretch", find_clear_stretch(fake_hours([90, 10, 90, 90])) is None)

print("conditions:")
moon_dark = {"phase_pct": 2.0, "phase_name": "New Moon", "is_up": False,
             "rising": None, "setting": None}
hours = fake_hours([5, 10, 5, 0, 10, 5])
s, msg = assess_conditions({"hours": hours}, moon_dark, find_clear_stretch(hours), moonlit=1.0)
check("new moon up all night still scores 10", s == 10, f"got {s}: {msg}")

hours = fake_hours([95, 90, 10, 5, 5, 10])
s, msg = assess_conditions({"hours": hours}, moon_dark, find_clear_stretch(hours), moonlit=0.0)
check("late clearing still scores high", s >= 9 and "clears" in msg, f"got {s}: {msg}")

hours = fake_hours([100] * 6)
s, msg = assess_conditions({"hours": hours}, moon_dark, find_clear_stretch(hours), moonlit=0.0)
check("socked-in night fails threshold", s < 6, f"got {s}: {msg}")

moon_full = dict(moon_dark, phase_pct=95.0, is_up=True)
hours = fake_hours([5] * 6)
s, msg = assess_conditions({"hours": hours}, moon_full, find_clear_stretch(hours), moonlit=1.0)
check("full moon up all night kills the night", s < 6, f"got {s}: {msg}")

s, msg = assess_conditions({"hours": hours}, moon_full, find_clear_stretch(hours), moonlit=0.2)
check("full moon that sets early barely dings", s == 9, f"got {s}: {msg}")

moon_half = dict(moon_dark, phase_pct=55.0, is_up=True)
s, msg = assess_conditions({"hours": hours}, moon_half, find_clear_stretch(hours), moonlit=1.0)
check("half moon dings but doesn't kill", s == 7, f"got {s}: {msg}")

print("window clamping:")
night = {"window_start": local_to_ephem(base), "window_end": local_to_ephem(base + timedelta(hours=8)),
         "prime_end": local_to_ephem(base + timedelta(hours=4)),
         "start_local": base, "end_local": base + timedelta(hours=8)}
stretch = fake_hours([10, 10, 10], start=base + timedelta(hours=3))
eff = effective_night(night, stretch)
check("imaging window starts at clearing", eff["start_local"] == base + timedelta(hours=3))
check("imaging window ends after last clear hour", eff["end_local"] == base + timedelta(hours=6))
check("prime cutoff unchanged", eff["prime_end"] == night["prime_end"])
check("no stretch leaves window unchanged", effective_night(night, None) is night)
full = fake_hours([10] * 9, start=base)
check("full-night stretch keeps full window", effective_night(night, full)["window_end"] == night["window_end"])

print("tonight's window (live ephem, offline):")
night = get_night()
check("window ordered", night["window_start"] < night["window_end"])
check("window is 3-14 hours", 3 < (night["window_end"] - night["window_start"]) * 24 < 14)
check("prime end within window", night["window_start"] <= night["prime_end"] <= night["window_end"])
check("dark starts after sunset", night["window_start"] > night["sunset"])

print("tonight's recommendations (live ephem, offline):")
import targets as targets_mod
saved = targets_mod.HORIZON_MASK, targets_mod.MIN_ALTITUDE
try:
    targets_mod.HORIZON_MASK, targets_mod.MIN_ALTITUDE = [], -90.0
    unmasked = targets_mod.get_recommendations(night)
    check("no mask keeps the whole catalog", len(unmasked) == len(DSO_CATALOG))
finally:
    targets_mod.HORIZON_MASK, targets_mod.MIN_ALTITUDE = saved
masked = targets_mod.get_recommendations(night)
check("mask only ever removes targets", len(masked) <= len(unmasked))
check("no blocked peak survives the mask",
      all(not is_blocked(t["altitude"], t["azimuth"]) for t in masked))

print(f"\n{passed} checks passed")
