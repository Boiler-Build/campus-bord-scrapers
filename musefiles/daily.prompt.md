# The goal

Get events happening on campus for Purdue in Indianapolis and send them to an api. These events should come from various instragram pages.

# Pages to search


- @purdueindy — main campus
- @psub_indy — PSUB
- @cco_purdueindy
- @purduehonors_indy

CS / tech

- @csclub_purdueindy
- @cswn.indy
- @purdue_usbindy
- @purdue_indy_ecess
- @purdue_indy_builds
- @purdue.mit
- @wicys_purdueindy
- @pui.swe
- @colorstackpurdueindy
- @purdueappliedcreativecomputing
- @hackindy — 0 posts as of Oct 19
- @amplifypurdue
- @purdue_startup_indy
- @buildpurdue

Engineering / science / robotics

- @pui_asme
- @bioforge_purdue / @bmespurdue
- @boilersub
- @boilergp — dormant as of Oct 19
- @pindyrobotics
- @purdue_roboracer
- @src.purdue
- @purduefirst_indy
- @pesc_indy
- @purduemotorsportsengineering

Culture / identity / professional

- @hispanosunidos_pui
- @pui.nsbe
- @shpe_pui
- @purdueindymsa
- @lcmsu_purdue_indianapolis
- @ppaindy

Arts / life / sports

- @steam_pui
- @purduemixedmedia
- @pmcindianapolis
- @pcc_pin
- @sdo.purdueindy
- @purdueindybadminton
- @purdueindychess
- @indyclimbingclub
- @mensclubvb_at_purdue_indy
- @purdue_tkd_indy
- @boilerleagueindy
- @purdueskiclub
- @purdue_pi.med


# The api

## How to send an api request

Submitting events to the api can be described by this python code:
```
req_headers = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.10 Safari/605.1.1',
}
route = 'https://campusbord.com/api/event/batch_upload'
SIZE_LIMIT = 5

async def postEvents(events, sizeLimit=SIZE_LIMIT):
  for i in range(len(events["events"])//sizeLimit + 1):
    batch = {"events": events["events"][i*sizeLimit:(i+1)*sizeLimit]}
    try:
      req = requests.post(route, headers=req_headers, json=batch)#, verify='campusbord-com-chain.pem')
    except:
      print("\nRequest Failed")
```

## json formatting

The json format for the api request should be as follows:
```
{
  "events": [
    {
        "Title": "{Title/Name of the event}",
        "org": "{Name of the organization holding the event}",
        "date": "{%a %b %d %Y}",
        "start": "{%A, %B %d %Y at %I:%M %p}",
        "end": "{%A, %B %d %Y at %I:%M %p}",
        "bldg": "{Pick one from the code block below}",
        "room": "{What room the event is in}",
        "email": "scraper@insta.scraper",
        "desc": "{Description of the event followed by the instragram's handle and a link to the post}",
        "tags": [
            "{Pick up to 3 from the code block below}"
        ],
        "image": "{Base64 Encoding of the image for the event}"
    }
  ]
}
```
Anything inside of curly brackets should be replaced with the appropriate information. If there are no curly brackets around a field, it should be left unmodified. You are allowed to add more events inside the events array, but do not exceed the size limit specified by the example code above.


Below is a list of tags and buildings you may use for the event json request.
```
{
    "tags": [
        "Social",
        "Academic",
        "Career",
        "Cultural",
        "Food",
        "Sport",
        "Art",
        "Music",
        "Purdue",
        "IU"
    ],
    "buildings": [
        "North Hall",
        "Lux",
        "Campus Center",
        "Boiler Park",
        "Library",
        "Student Center",
        "ET",
        "SL",
        "IO",
        "IT",
        "STT",
        "Tower",
        "AD",
        "BS",
        "CA",
        "EL",
        "ES",
        "HR",
        "IF",
        "IH",
        "IP",
        "LD",
        "LE",
        "MT",
        "NU",
        "PE",
        "UC",
        "UH",
        "UL"
    ]
}
```

# Criteria
Look for events that are happening in Purdue Indianapolis, not West Lafayette. 

Look for several events that are happening in the next 7 days. Don't include any events that have already happened. 

If there is no start time for the event, do not include it. If no end time is listed, assume 1 hour.

Only include an image that holds information about the event. If the image is just a picture of a person or a group of people, do not include it. If the image is a poster for the event, include it. 

When adding tags, you may add anywhere from 0 to 3. Try to add as many as possible, but if there are no more relevant tags, do not add any more.

Keep a list of all the instagram pages you scraped from. Store this list in your memory.md. If there is a duplicate instagram page, don't add it again.
