# The goal

Get events happening on campus for Purdue in Indianapolis and send them to an api. These events should come from various instragram pages.

# Pages to search

- @purdue_usbindy
- @csclub_purdueindy
- @purdueindymsa
- @cswn.indy
- @psub_indy
- @purdue_pi.med
- @purdue_roboracer
- @thecsoffice
- @pmcindianapolis
- @purdue_tkd_indy
- @purduemixedmedia

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

TODO: list criteria for things that we MUST have.

# Exceptions

#TODO: list any edge cases such as duplicate events or no images.