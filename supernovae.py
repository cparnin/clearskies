"""Exploding stars in tonight's visible sky: bright supernovae, plus novae
in the Andromeda Galaxy.

Source: David Bishop's pages at rochesterastronomy.org, updated daily from
TNS and ATel. The Latest Supernovae page's "All active supernova" summary
table lists each object's latest magnitude, type, and host galaxy, with the
host's coordinates in the link - close enough to the supernova for
scheduling, and the host is what gets framed anyway. The Extragalactic Novae
page has one free-text entry per nova, each with a "Mag 15.4:4/9" line
giving its latest magnitude and the month/day it was measured.
"""

import re
from datetime import date, datetime, timedelta
from html import unescape

import requests

from astro import LOCAL_TZ, get_night
from config import SN_MAX_MAG
from targets import evaluate_target

SN_URL = "https://www.rochesterastronomy.org/supernova.html"
NOVA_URL = "https://www.rochesterastronomy.org/novae.html"
SN_MAX_COUNT = 2  # supernova lines per notification
NOVA_MAX_AGE_DAYS = 7  # novae fade within days, so older magnitudes are stale
M31_RA, M31_DEC = "0:42:44", "41:16:09"  # novae sit within a degree of the core

_TABLE = re.compile(r"All active supernova over mag.*?</table>", re.S | re.I)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_COORDS = re.compile(r"[?&](?:amp;)?ra=(-?[\d.]+)&(?:amp;)?de=(-?[\d.]+)", re.I)
# Classified supernova types: Ia, II, IIP, IIn, Ib/c, Ic-BL, SLSN-I ... -
# not "unk" candidates, novae, AGN, or other impostors
_SN_TYPE = re.compile(r"^(I|SLSN)")
_NO_HOST = {"", "none", "anonymous"}

# Each novae-page entry opens with an anchor on its TNS name, e.g. <a id="2026jnl">
_NOVA_ENTRY = re.compile(r'<a id="\d{4}[a-z]+">')
_NOVA_MAG = re.compile(r"Mag\s+([\d.]+):(\d{1,2})/(\d{1,2})")
_DISCOVERED = re.compile(r"discovered (\d{4})/(\d{2})/(\d{2})")
_IN_M31 = re.compile(r"Found in M31\b|host M31\)")
_M31_NAME = re.compile(r"(?:Nova M31|M31N) (\d{4}-\d{2}[a-z]+)")
_TNS_NAME = re.compile(r"\b(?:AT|SN) ?\d{4}[a-z]+")


def parse_active_supernovae(html: str) -> list:
    """Rows of the page's active-supernova summary table.

    Each: name, mag (latest), stale (latest observation over a month old),
    type, host (None when there's no named host), ra (hours), dec (degrees).
    """
    table = _TABLE.search(html)
    if not table:
        return []

    rows = []
    for row in _ROW.findall(table.group(0)):
        cells = _CELL.findall(row)
        if len(cells) < 4:
            continue  # header row (<th>) or malformed
        name, mag, sn_type, host = (_TAG.sub("", c).strip() for c in cells[:4])
        coords = _COORDS.search(cells[3])
        try:
            mag_val = float(mag.rstrip("*"))
        except ValueError:
            continue
        if not coords or not name:
            continue
        rows.append({
            "name": f"SN {name}" if name[:1].isdigit() else name,
            "mag": mag_val,
            "stale": mag.endswith("*"),
            "type": sn_type,
            "host": None if host.lower() in _NO_HOST else host,
            "ra": float(coords.group(1)),
            "dec": float(coords.group(2)),
        })
    return rows


def is_candidate(sn: dict, max_mag: float = None) -> bool:
    """Bright enough, classified as a supernova, and recently observed."""
    max_mag = SN_MAX_MAG if max_mag is None else max_mag
    return sn["mag"] <= max_mag and not sn["stale"] and bool(_SN_TYPE.match(sn["type"]))


def _observed_on(month: int, day: int, discovered: date) -> date | None:
    """Resolve a "4/9"-style observation date against the discovery date
    (an observation months 'before' discovery belongs to the next year)."""
    try:
        observed = date(discovered.year, month, day)
    except ValueError:
        return None
    if observed < discovered - timedelta(days=60):
        observed = observed.replace(year=observed.year + 1)
    return observed


def parse_m31_novae(html: str) -> list:
    """Andromeda novae on the novae page: name, mag (latest), observed (date)."""
    novae = []
    for chunk in _NOVA_ENTRY.split(html)[1:]:
        text = " ".join(unescape(_TAG.sub(" ", chunk)).split())
        mag, found = _NOVA_MAG.search(text), _DISCOVERED.search(text)
        if not (_IN_M31.search(text) and mag and found):
            continue
        observed = _observed_on(int(mag[2]), int(mag[3]),
                                date(int(found[1]), int(found[2]), int(found[3])))
        designation, tns = _M31_NAME.search(text), _TNS_NAME.search(text)
        name = f"M31N {designation[1]}" if designation else (tns[0] if tns else None)
        if observed and name:
            novae.append({"name": name, "mag": float(mag[1]), "observed": observed})
    return novae


def is_fresh_nova(nova: dict, today: date, max_mag: float = None) -> bool:
    """Bright enough and measured within the last NOVA_MAX_AGE_DAYS."""
    max_mag = SN_MAX_MAG if max_mag is None else max_mag
    age = (today - nova["observed"]).days
    return nova["mag"] <= max_mag and -1 <= age <= NOVA_MAX_AGE_DAYS


def _fetch(url: str, label: str) -> str | None:
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "ClearSkies/1.0"})
        response.raise_for_status()
    except Exception as e:
        print(f"{label} fetch failed: {e}")
        return None
    return response.content.decode("latin-1")  # pages declare iso-8859-1


def get_andromeda_novae(night: dict = None, today: date = None) -> list:
    """The brightest fresh nova in M31, if M31 is in the visible sky tonight.

    Never raises: a fetch or parse failure just means no nova line.
    """
    if SN_MAX_MAG <= 0:
        return []  # alerts turned off
    night = night or get_night()
    today = today or datetime.now(LOCAL_TZ).date()

    html = _fetch(NOVA_URL, "Nova")
    if html is None:
        return []
    novae = sorted((n for n in parse_m31_novae(html) if is_fresh_nova(n, today)), key=lambda n: n["mag"])
    if not novae:
        return []
    t = evaluate_target(novae[0]["name"], M31_RA, M31_DEC, "nova", "hard", None, night)
    if t is None:
        return []  # Andromeda isn't in the visible sky tonight
    t.update(mag=novae[0]["mag"], sn_type="nova", host="Andromeda")
    return [t]


def get_supernovae(night: dict = None) -> list:
    """Bright supernovae reachable in tonight's visible sky, brightest first.

    Never raises: a fetch or parse failure just means no supernova line.
    """
    if SN_MAX_MAG <= 0:
        return []  # supernova alerts turned off
    night = night or get_night()

    html = _fetch(SN_URL, "Supernova")
    if html is None:
        return []

    picks = []
    for sn in parse_active_supernovae(html):
        if not is_candidate(sn):
            continue
        t = evaluate_target(sn["name"], str(sn["ra"]), str(sn["dec"]), "supernova", "hard", None, night)
        if t is None:
            continue  # never enters the visible sky tonight
        t.update(mag=sn["mag"], sn_type=sn["type"], host=sn["host"])
        picks.append(t)

    picks.sort(key=lambda t: t["mag"])
    return picks[:SN_MAX_COUNT]


def get_exploding_stars(night: dict = None) -> list:
    """Supernovae, then any Andromeda nova, for the notification."""
    night = night or get_night()
    return get_supernovae(night) + get_andromeda_novae(night)


if __name__ == "__main__":
    night = get_night()
    sne = get_exploding_stars(night)
    if not sne:
        print(f"No supernovae or Andromeda novae brighter than mag {SN_MAX_MAG} in your sky tonight.")
    for t in sne:
        host = f" in {t['host']}" if t["host"] else ""
        late = " (overnight)" if t["is_late"] else ""
        print(f"{t['name']}{host}: {t['sn_type']}, mag {t['mag']}, best {t['peak_time']} "
              f"@ {t['altitude']}° az {t['azimuth']:.0f}°{late}")
