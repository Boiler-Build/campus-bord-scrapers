from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import asyncio
import requests
from datetime import datetime, timedelta, timezone, date, time
import pytz
from boilerlink import formatEvents, writeOutput, postEvents

link = "https://purdueme.com/events/category/indianapolis/"

def main():
  #parse event links
  events = parseEvents()

  #backup write incase format or post fails
  writeOutput(events)

  #format events
  events = formatEvents(events)

  #send events to route with size limit of 1
  asyncio.run(postEvents(events, 1))

  #write output to json (for debugging)
  writeOutput(events)

def parseEvents():
  with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    page.goto(link)
    page.wait_for_load_state('networkidle')

    soup = BeautifulSoup(page.content(), 'html.parser')
    events = {"events": []}

    eventDivs = soup.find_all(class_='tribe-common-g-row tribe-events-calendar-list__event-row')

    for eventDiv in eventDivs:
      title = eventDiv.find(class_='tribe-events-calendar-list__event-title-link tribe-common-anchor-thin')
      orgs = 'Purdue'
      location = eventDiv.find(class_='tribe-events-calendar-list__event-venue-title tribe-common-b2--bold')
      description = ''
      start = eventDiv.find(class_='tribe-event-date-start')
      end = eventDiv.find(class_='tribe-event-time')
      email = 'scraper@scraper.com'
      categories = ''
      perks = ''
      imageurl = eventDiv.find('img')

      data = {
        "title": title,
        "org": orgs,
        "loc": location,
        "desc": description,
        "startTime": start,
        "endTime": end,
        "email": email,
        "categories": categories,
        "perks": perks,
        "image": imageurl,
      }

      requiredElements = ['title', 'loc', 'startTime', 'image']
      if any([not data[key] for key in requiredElements]):
        continue

      requiredText = ['title', 'loc', 'startTime']
      for key in requiredText:
        data[key] = data[key].get_text().strip()
      data['image'] = data['image'].get('src')

      #not adding virtual events
      if data['loc'] == "Online" or data['loc'] == "Virtual":
        continue

      #multi day events not adding
      if '@' not in data['startTime']:
        continue

      data['startTime'] = toUnix(data['startTime'])

      if data['endTime'] == None:
        data['endTime'] = data['startTime'] + (60 * 60 * 1000)
      else:
        data['endTime'] = formatEndDate(data['endTime'].get_text().strip(), data['startTime'])

      events["events"].append(data)

  return events

def toUnix(date):
  #input format: September 14 @ 1:30 PM
  formatDate = "%B %d @ %I:%M %p"
  formatDate = datetime.strptime(date, formatDate)

  #add correct year
  today = datetime.today()
  year = today.year + 1 if (today.month, today.day) > (formatDate.month, formatDate.day) else today.year
  formatDate = formatDate.replace(year=year)

  timezone = pytz.timezone("US/Eastern")
  formatDate = timezone.localize(formatDate)
  unix = int(formatDate.timestamp()) * 1000

  return unix

def formatEndDate(date, start):
  formatDate = "%I:%M %p"
  formatDate = datetime.strptime(date, formatDate)

  start = datetime.fromtimestamp(start / 1000)

  formatDate = start.replace(hour=formatDate.hour, minute=formatDate.minute)

  timezone = pytz.timezone("US/Eastern")
  formatDate = timezone.localize(formatDate)
  unix = int(formatDate.timestamp()) * 1000

  return unix


if __name__ == '__main__':
  main()