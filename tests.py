"""Offline sanity tests - no network needed. Run: python tests.py"""

from datetime import datetime, timedelta

from astro import LOCAL_TZ, get_night, local_to_ephem
from config import _parse_horizon_mask
from main import assess_conditions, build_message, display_name, effective_night, find_clear_stretch
from datetime import date

from supernovae import is_candidate, is_fresh_nova, parse_active_supernovae, parse_m31_novae
from targets import DSO_CATALOG, SHOWPIECES, best_moment, is_blocked, score_target

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
check("round-off past 360 still counts as north",
      not is_blocked(50.0, 360.00001, mask=[(180, 360, 90)], min_altitude=0.0)
      and is_blocked(50.0, 359.9, mask=[(180, 360, 90)], min_altitude=0.0))
check("env mask parsing",
      _parse_horizon_mask("250-340:90,340-20:35") == [(250.0, 340.0, 90.0), (340.0, 20.0, 35.0)])

print("best moment (track = (time, alt, az) samples):")
EAST_ONLY = [(180, 360, 90)]
# Veil East on 8/11: 76° at the 11 PM cutoff, 86° peak around 1 AM
pick = best_moment([(3, 70.0, 30.0), (4, 76.0, 12.0), (5, 86.4, 0.0)], 4, mask=[], min_altitude=30.0)
check("near-peak by cutoff counts as prime", pick[0] == 4, f"got {pick}")
pick = best_moment([(4, 40.0, 90.0), (6, 80.0, 120.0)], 4, mask=[], min_altitude=30.0)
check("still climbing stays overnight", pick[0] == 6, f"got {pick}")
pick = best_moment([(3, 25.0, 220.0), (4, 50.0, 300.0), (5, 55.0, 220.0)], 4,
                   mask=[(250, 340, 90)], min_altitude=30.0)
check("blocked at cutoff stays overnight", pick[0] == 5, f"got {pick}")
pick = best_moment([(4, 25.0, 90.0), (5, 35.0, 100.0)], 4, mask=[], min_altitude=30.0)
check("below floor at cutoff stays overnight", pick[0] == 5, f"got {pick}")
south_transit = [(1, 40.0, 120.0), (2, 55.0, 150.0), (3, 59.0, 175.0), (3.2, 60.0, 180.0),
                 (4, 55.0, 210.0), (5, 40.0, 240.0)]
pick = best_moment(south_transit, 10, mask=EAST_ONLY, min_altitude=30.0)
check("east-only sky shoots a south transit on its climb", pick == (3, 59.0, 175.0), f"got {pick}")
check("clear sky shoots it at the true peak",
      best_moment(south_transit, 10, mask=[], min_altitude=30.0)[1] == 60.0)
check("target only in the blocked west is dropped",
      best_moment([(1, 50.0, 250.0), (2, 40.0, 270.0)], 10, mask=EAST_ONLY, min_altitude=30.0) is None)
check("target never above the floor is dropped",
      best_moment([(1, 20.0, 90.0), (2, 25.0, 100.0)], 10, mask=[], min_altitude=30.0) is None)

print("display names:")
check("catalog prefix dropped", display_name("M8 - Lagoon Nebula") == "Lagoon Nebula")
check("NGC prefix dropped", display_name("NGC 2174 - Monkey Head") == "Monkey Head")
check("descriptive suffix kept", display_name("Veil Nebula - East") == "Veil Nebula - East")
check("bare designations kept", display_name("M77 + NGC 1055") == "M77 + NGC 1055")
check("plain name unchanged", display_name("Iris Nebula") == "Iris Nebula")

print("supernovae (synthetic page in the real format):")
SN_PAGE = """<a id="News"></a>
<b>All active supernova over mag 17.0</b>
<table>
<tr><th>Name</th><th>Mag</th><th>Type</th><th>Host</th></tr>
<tr><td><a href="#2026tst" target="_self">2026tst</a></td><td>13.3</td><td>Ia-CSM</td><td><a href="http://www.wikisky.org/?ra=22.618227&de=34.409824&zoom=10&show_box=1&box_width=50">NGC 7331</a></td></tr>
<tr><td><a href="#2026old" target="_self">2026old</a></td><td>14.1*</td><td>II</td><td><a href="http://www.wikisky.org/?ra=13.395941&de=31.564491&zoom=10&show_box=1&box_width=50">NGC 5127</a></td></tr>
<tr><td><a href="#2026unk" target="_self">AT2026unk</a></td><td>12.9</td><td>unk</td><td><a href="http://www.wikisky.org/?ra=13.430447&de=-5.678900&zoom=10&show_box=1&box_width=50">none</a></td></tr>
<tr><td><a href="#2026dim" target="_self">2026dim</a></td><td>16.9</td><td>IIn</td><td><a href="http://www.wikisky.org/?ra=9.093177&de=-15.886727&zoom=10&show_box=1&box_width=50">anonymous</a></td></tr>
</table>
<table><tr><td>2026zzz</td><td>9.0</td><td>Ia</td><td><a href="?ra=1&de=1">elsewhere</a></td></tr></table>"""
sne = parse_active_supernovae(SN_PAGE)
check("parses only the summary table's data rows", [x["name"] for x in sne] ==
      ["SN 2026tst", "SN 2026old", "AT2026unk", "SN 2026dim"], f"got {[x['name'] for x in sne]}")
check("host coordinates and magnitude parsed",
      (sne[0]["ra"], sne[0]["dec"], sne[0]["mag"], sne[0]["host"]) == (22.618227, 34.409824, 13.3, "NGC 7331"))
check("starred magnitude is stale", sne[1]["stale"] and sne[1]["mag"] == 14.1 and not sne[0]["stale"])
check("no named host becomes None", sne[2]["host"] is None and sne[3]["host"] is None)
check("bright classified fresh supernova is a candidate", is_candidate(sne[0], max_mag=15))
check("stale observation is not", not is_candidate(sne[1], max_mag=15))
check("unclassified transient is not", not is_candidate(sne[2], max_mag=15))
check("too faint is not, until the limit allows it",
      not is_candidate(sne[3], max_mag=15) and is_candidate(sne[3], max_mag=17))
check("page without the table yields nothing", parse_active_supernovae("<html>moved</html>") == [])

msg_night = {"window_start": 0, "window_end": 1}
msg_moon = {"phase_pct": 2.0, "phase_name": "New Moon", "is_up": False, "rising": None, "setting": None}
sn_pick = {"name": "SN 2026tst", "host": "NGC 7331", "sn_type": "Ia-CSM", "mag": 13.3,
           "peak_time": "7:30 PM", "is_late": False}
gal_pick = {"name": "M31 - Andromeda Galaxy", "peak_time": "9 PM", "is_late": False}
msg = build_message("Excellent conditions!", msg_night, msg_night, msg_moon, [gal_pick], [sn_pick])
check("notification gets a supernova line",
      "**💥 Exploding stars**" in msg and "• SN 2026tst in NGC 7331 (Ia-CSM, mag 13.3) — best 7:30 PM" in msg, msg)
msg = build_message("Excellent conditions!", msg_night, msg_night, msg_moon, [gal_pick],
                    [dict(sn_pick, host=None, is_late=True)])
check("hostless overnight supernova line", "• SN 2026tst (Ia-CSM, mag 13.3) — best 7:30 PM (overnight)" in msg, msg)
check("no exploding-star section when there are none",
      "Exploding" not in build_message("Excellent conditions!", msg_night, msg_night, msg_moon, [gal_pick]))

print("andromeda novae (synthetic page in the real format):")
NOVA_PAGE = """<a id="Latest"></a>
<td valign="top"><font face="Arial" size="2">
<a id="2026tsa">AT2026tsa</a>
(= <a id="NM312611a">Nova M31 2026-11a</a>) (= PNV J00433836+4115324),
<a href="https://www.wis-tns.org/object/2026tsa">TNS</a>
discovered 2026/11/05.079 by
Someone et al.
<br />Found in <a href="https://ned.ipac.caltech.edu/byname?
objname=M31&img_stamp=YES">M31</a>
at <a href="http://www.wikisky.org/?ra=0.727322&de=41.258999"
>R.A. = 00h43m38s.520, Decl. = +41&deg;16'13".50</a>
<br />Mag 14.6:11/7, Type unknown (zhost=-0.001004)
</font></td>
<td><a id="2026tsb">AT2026tsb</a> (= M31N 2026-10b), discovered 2026/10/01.100 by ZTF
<br />Found in <a href="x">M31</a> at R.A. = 00h42m20s.480
<br />Mag 14.2:10/2, Type EGN</td>
<td><a id="2026tsc">AT2026tsc</a> (= ASASSN-26fv) discovered 2026/11/06.160
at R.A. = 05h37m54s.415, Decl. = -69&deg;54'54".00 Mag 12.4:11/8, Type unknown (host LMC)</td>
<td><a id="2025tsd">AT2025tsd</a> discovered 2025/12/28.100 by XOSS
<br />Found in <a href="x">M31</a> at R.A. = 00h43m30s.830
<br />Mag 18.1:1/3, Type unknown</td>"""
novae = parse_m31_novae(NOVA_PAGE)
check("only M31 entries, named by designation or TNS name",
      [n["name"] for n in novae] == ["M31N 2026-11a", "M31N 2026-10b", "AT2025tsd"], f"got {novae}")
check("latest magnitude and its date parsed",
      (novae[0]["mag"], novae[0]["observed"]) == (14.6, date(2026, 11, 7)))
check("observation after new year rolls the year", novae[2]["observed"] == date(2026, 1, 3))
today = date(2026, 11, 9)
check("bright nova seen 2 days ago is fresh", is_fresh_nova(novae[0], today, max_mag=15))
check("nova seen 5 weeks ago is stale", not is_fresh_nova(novae[1], today, max_mag=15))
check("faint nova is not", not is_fresh_nova(dict(novae[0], mag=16.2), today, max_mag=15))
msg = build_message("Excellent conditions!", msg_night, msg_night, msg_moon, [gal_pick],
                    [dict(sn_pick, name="M31N 2026-11a", host="Andromeda", sn_type="nova", mag=14.6)])
check("nova line names Andromeda", "• M31N 2026-11a in Andromeda (nova, mag 14.6) — best 7:30 PM" in msg, msg)

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

# Regression: GitHub's scheduler can start the run hours late. A run after
# sunset (or after dark) must still describe the same evening, not tomorrow.
evening = [get_night(LOCAL_TZ.localize(datetime(2026, 10, 3, h, 30))) for h in (16, 19, 21, 23)]
check("late start keeps tonight's sunset", len({round(n["sunset"], 4) for n in evening}) == 1)
check("late start keeps tonight's window", len({round(n["window_start"], 4) for n in evening}) == 1)
check("window is that evening", evening[0]["start_local"].date() == datetime(2026, 10, 3).date())

print("tonight's recommendations (live ephem, offline):")
import targets as targets_mod
ALL_TYPES = {"galaxy", "cluster", "nebula"}
saved = targets_mod.HORIZON_MASK, targets_mod.MIN_ALTITUDE
try:
    targets_mod.HORIZON_MASK, targets_mod.MIN_ALTITUDE = [], -90.0
    unmasked = targets_mod.get_recommendations(night, types=ALL_TYPES)
    check("no mask keeps the whole catalog", len(unmasked) == len(DSO_CATALOG))
    check("type filter keeps only those types",
          {t["type"] for t in targets_mod.get_recommendations(night, types={"galaxy"})} == {"galaxy"})
    check("no-nebula filter drops every nebula",
          all(t["type"] != "nebula" for t in targets_mod.get_recommendations(night, types={"galaxy", "cluster"})))

    # Regression: on 11/9 NGC 253 transits due south at ~10 PM. An east-only
    # sky must still recommend it on its climb, not drop it for peaking at 180°.
    targets_mod.HORIZON_MASK, targets_mod.MIN_ALTITUDE = EAST_ONLY, 30.0
    nov9 = get_night(LOCAL_TZ.localize(datetime(2026, 11, 9, 16, 0)))
    east = {t["name"]: t for t in targets_mod.get_recommendations(nov9, types=ALL_TYPES)}
    sculptor = east.get("NGC 253 - Sculptor Galaxy")
    check("east-only sky keeps a south-transiting galaxy",
          sculptor is not None and sculptor["azimuth"] < 180 and sculptor["altitude"] > 35, f"got {sculptor}")
    check("east-only sky keeps nothing in the west", all(t["azimuth"] < 180 for t in east.values()))
    sn = targets_mod.evaluate_target("SN 2026tst", "22.618227", "34.409824", "supernova", "hard", None, nov9)
    check("supernova at NGC 7331 is up in the east on 11/9", sn is not None and sn["azimuth"] < 180, f"got {sn}")
finally:
    targets_mod.HORIZON_MASK, targets_mod.MIN_ALTITUDE = saved
masked = targets_mod.get_recommendations(night, types=ALL_TYPES)
check("mask only ever removes targets", len(masked) <= len(unmasked))
check("no blocked best moment survives the mask",
      all(not is_blocked(t["altitude"], t["azimuth"]) for t in masked))
check("default run honors TARGET_TYPES",
      all(t["type"] in targets_mod.TARGET_TYPES for t in targets_mod.get_recommendations(night)))

print(f"\n{passed} checks passed")
