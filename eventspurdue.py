"""
Scraper for the Purdue University events calendar (events.purdue.edu),
limited to the "Purdue in Indianapolis" group.

events.purdue.edu runs on Localist, which has a public read-only JSON API,
so this uses plain requests (no Selenium/Playwright).
API docs: https://developer.localist.com/doc/api

Rules:
  - recurring events are not included
  - events without their own photo are kept (sent with no image) and always get a category

Run with DRY_RUN = True first and check events.json, then set it to False to post.
"""
import asyncio
import math
from collections import Counter
from datetime import datetime, timedelta, date
from time import sleep

import pytz
import requests

# Note: importing boilerlink also imports selenium, and boilerlink.py needs Python 3.12+
from boilerlink import formatEvents, writeOutput, postEvents, catperkToTag, GROUP

API_URL = "https://events.purdue.edu/api/2/events"
GROUP_ID = 46197580344207       # Localist group "Purdue in Indianapolis"
DEFAULT_ORG = "Purdue in Indianapolis"
DEFAULT_CATEGORY = "Social"     # category for photo-less events that match no other category
BATCH_SIZE = 5                  # events per POST
DAYS_TO_SEARCH = 7
PAGE_SIZE = 100                 # Localist max is 100
MAX_PAGES = 20                  # safety cap
REQUEST_DELAY = 1               # seconds between API pages
DRY_RUN = True                  # True = scrape + write events.json only, no POST

SKIP_TITLES_WITH = ["practice", "rehearsal"]
SKIP_ALL_DAY = True             # all-day listings are mostly deadlines/holidays ("Winter Recess")
SKIP_LOCATIONS = {"online", "virtual", "zoom", "microsoft teams"}

# Location filter: the group feed includes some events outside Indianapolis
CAMPUS_LAT, CAMPUS_LNG = 39.7743, -86.1765   # Purdue in Indianapolis campus
MAX_DISTANCE_KM = 5             # None to disable the distance check
OTHER_PLACES = ["west lafayette", "carmel", "fishers", "noblesville", "fort wayne",
                "mackey arena", "ross-ade"]

EASTERN = pytz.timezone("US/Eastern")
REQ_HEADERS = {"User-Agent": "campus-bord-scrapers (https://campusbord.com)"}

# Localist event types -> Campus Bord tags, matched by keyword in the type name.
# Unmatched type names are printed so this list can be extended.
TYPE_KEYWORDS = {
  "Food": ["food", "dining", "lunch", "dinner", "breakfast"],
  "Sport": ["athlet", "sport", "recreation", "fitness", "hockey", "basketball", "soccer"],
  "Career": ["career", "workshop", "training", "professional", "conference", "job", "internship"],
  "Academic": ["lecture", "seminar", "academic", "class", "research", "presentation",
               "colloquium", "symposium", "info session", "advisor", "advising", "study", "exam"],
  "Social": ["social", "festival", "celebration", "performance", "concert", "arts",
             "exhibit", "film", "music", "theatre", "theater", "party", "community"],
}
IGNORED_TYPES = {"featured", "dates and deadlines"}   # Localist types that say nothing about the category
FOOD_WORDS = ["free food", "refreshments", "pizza", "lunch provided", "lunch will be provided",
              "dinner provided", "snacks"]

# formatEvents maps categories through catperkToTag; make each tag map to itself
catperkToTag.update({tag: tag for tag in TYPE_KEYWORDS})


def main():
  events = parseEvents()
  print(f"\nKept {len(events['events'])} events")

  writeOutput(events)              # raw backup in case format/post fails
  if not events["events"]:
    return
  events = formatEvents(events)
  dropBrokenImages(events)

  if DRY_RUN:
    print("DRY_RUN: not posting. See events.json")
  else:
    asyncio.run(postEvents(events, BATCH_SIZE))

  writeOutput(events)


def fetchEvents(start, end):
  """Return raw Localist event dicts for the group between start (inclusive) and end (exclusive).

  Localist returns one row per occurrence, so an event with several dates appears several times.
  """
  rows, page, totalPages = [], 1, 1
  while page <= totalPages and page <= MAX_PAGES:
    params = {
      "group_id": GROUP_ID,
      "start": start.isoformat(),
      "end": end.isoformat(),
      "pp": PAGE_SIZE,
      "page": page,
    }
    data = getJson(params)
    rows += [item.get("event", item) for item in data.get("events", [])]
    totalPages = data.get("page", {}).get("total", 1) or 1
    page += 1
    if page <= totalPages:
      sleep(REQUEST_DELAY)
  return rows


def getJson(params, retries=1):
  for attempt in range(retries + 1):
    try:
      res = requests.get(API_URL, params=params, headers=REQ_HEADERS, timeout=30)
      res.raise_for_status()
      return res.json()
    except (requests.RequestException, ValueError) as e:
      if attempt == retries:
        raise RuntimeError(f"Localist API request failed: {e}") from e
      print(f"Request failed ({e}), retrying in 3 seconds")
      sleep(3)


def parseEvents():
  events = {"events": []}
  today = date.today()
  lastDay = today + timedelta(days=DAYS_TO_SEARCH)
  windowStart, windowEnd = toMillisFromDate(today), toMillisFromDate(lastDay)

  rows = fetchEvents(today, lastDay)
  occurrences = Counter(ev.get("id") for ev in rows)
  reported = set()          # so an event with several rows is only reported once
  unmappedTypes = set()

  def skip(ev, reason):
    if ev.get("id") not in reported:
      reported.add(ev.get("id"))
      print(f"Skipped ({reason}): {ev.get('title', '').strip()}")

  for ev in rows:
    title = (ev.get("title") or "").strip()
    instances = ev.get("event_instances") or []
    if not title or not instances:
      continue
    if ev.get("recurring") or occurrences[ev.get("id")] > 1 or len(instances) > 1:
      skip(ev, "recurring")
      continue
    if any(s in title.lower() for s in SKIP_TITLES_WITH):
      skip(ev, "title filter")
      continue
    if ev.get("experience") == "virtual":
      skip(ev, "virtual")
      continue
    problem = locationProblem(ev)
    if problem:
      skip(ev, problem)
      continue

    loc = locationText(ev)
    if not loc:
      skip(ev, "no location")
      continue
    if loc.lower() in SKIP_LOCATIONS:
      skip(ev, "online location")
      continue

    inst = instances[0].get("event_instance", instances[0])
    if inst.get("all_day") and SKIP_ALL_DAY:
      skip(ev, "all day")
      continue
    if not inst.get("start"):
      continue
    start = isoToMillis(inst["start"])
    end = isoToMillis(inst["end"]) if inst.get("end") else start + 60 * 60 * 1000
    if not (windowStart <= start < windowEnd):
      continue

    # Localist fills in a generic campus photo when an event has none; photo_id is only set for a real one
    hasPhoto = bool(ev.get("photo_id") and ev.get("photo_url"))
    desc = (ev.get("description_text") or "").strip()
    categories, unmapped = eventCategories(ev, title, desc, requireCategory=not hasPhoto)
    unmappedTypes |= unmapped

    data = {
      "title": title,
      "org": orgName(ev),
      "loc": loc,
      "desc": desc,
      "startTime": start,
      "endTime": end,
      "email": "purdueeventsscraper@scraper.com",
      "categories": sorted(categories),
      "perks": [],
    }
    if hasPhoto:
      data["image"] = ev["photo_url"]    # formatEvents turns it into base64 + imageType

    print(f"{title}  [{', '.join(data['categories']) or 'no category'}]{'' if hasPhoto else '  (no photo)'}")
    events["events"].append(data)

  if unmappedTypes:
    print(f"\nEvent types with no tag mapping (add to TYPE_KEYWORDS if useful): {sorted(unmappedTypes)}")

  return events


def locationProblem(ev):
  """Return why an event is outside the campus area, or None if it's fine."""
  geo = ev.get("geo") or {}
  city = (geo.get("city") or "").strip()
  if city:
    if city.lower() != "indianapolis":
      return f"in {city}"
  else:
    text = " ".join(str(ev.get(k) or "") for k in ("location_name", "location", "address")).lower()
    for place in OTHER_PLACES:
      if place in text:
        return f"at {place.title()}"

  if MAX_DISTANCE_KM is not None:
    try:
      lat, lng = float(geo.get("latitude")), float(geo.get("longitude"))
    except (TypeError, ValueError):
      return None   # no coordinates: trust the group
    km = distanceKm(lat, lng, CAMPUS_LAT, CAMPUS_LNG)
    if km > MAX_DISTANCE_KM:
      return f"{km:.0f} km from campus"
  return None


def locationText(ev):
  name = (ev.get("location_name") or ev.get("location") or "").strip()
  room = str(ev.get("room_number") or "").strip()
  if name and room:
    return f"{name}, {room}"
  return name or room or (ev.get("address") or "").strip()


def orgName(ev):
  departments = [d.get("name") for d in ev.get("departments") or [] if d.get("name")]
  if departments:
    return "\n".join(departments)
  groups = [g.get("name") for g in ev.get("groups") or []
            if g.get("name") and g.get("id") != GROUP_ID]
  return "\n".join(groups) if groups else DEFAULT_ORG


def matchKeywords(text):
  text = text.lower()
  return {tag for tag, words in TYPE_KEYWORDS.items() if any(w in text for w in words)}


def eventCategories(ev, title, desc, requireCategory=False):
  """Return (set of Campus Bord tags, set of Localist type names that matched nothing).

  With requireCategory, the result always has at least one tag: from the event types,
  then from the title/description, then DEFAULT_CATEGORY.
  """
  tags, unmapped = set(), set()
  typeNames = [t.get("name", "") for t in (ev.get("filters") or {}).get("event_types") or []]
  for name in typeNames:
    if not name or name.lower() in IGNORED_TYPES:
      continue
    matched = matchKeywords(name)
    tags |= matched
    if not matched:
      unmapped.add(name)

  # Localist's "free" flag means free entry, not free food, so look for food in the text
  if any(w in f"{title} {desc}".lower() for w in FOOD_WORDS):
    tags.add("Food")

  if requireCategory and not tags:
    tags = matchKeywords(title) or matchKeywords(desc) or {DEFAULT_CATEGORY}
  return tags, unmapped


def dropBrokenImages(events):
  """After formatEvents: if an image download failed (e.g. a 403 page came back instead of a
  picture), send the event without an image, and make sure it has a real category."""
  for e in events["events"]:
    if "image" in e and not str(e.get("imageType", "")).startswith("image/"):
      print(f"Image download failed, sending without image: {e['title']}")
      del e["image"]
      e.pop("imageType", None)
      if e["tags"] == [GROUP]:
        e["tags"] = sorted(matchKeywords(e["title"]) or matchKeywords(e["desc"]) or {DEFAULT_CATEGORY})


def isoToMillis(s):
  """Localist times are ISO 8601 with an offset, e.g. 2026-11-10T12:00:00-05:00."""
  dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
  if dt.tzinfo is None:
    dt = EASTERN.localize(dt)
  return int(dt.timestamp()) * 1000


def toMillisFromDate(d):
  return int(EASTERN.localize(datetime.combine(d, datetime.min.time())).timestamp()) * 1000


def distanceKm(lat1, lng1, lat2, lng2):
  r = 6371
  p1, p2 = math.radians(lat1), math.radians(lat2)
  dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
  a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
  return 2 * r * math.asin(math.sqrt(a))


if __name__ == "__main__":
  main()
