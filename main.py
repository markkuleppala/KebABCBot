# https://www.abcasemat.fi/fi/asemat

import asyncio
from pprint import pprint
import time
import math
from dotenv import load_dotenv
import os
import json
from bs4 import BeautifulSoup
from selenium import webdriver
import asyncio
import telepot
import telepot.aio
from telepot.aio.loop import MessageLoop
from datetime import datetime

def getDistance(src, dst):
    # Radius of Earth
    R = 6373.0

    lat1 = math.radians(float(src[0]))
    lon1 = math.radians(float(src[1]))
    lat2 = math.radians(dst[0])
    lon2 = math.radians(dst[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    # Round result and return with one decimal
    return float('{:.1f}'.format(round(distance, 1)))

def getClosest(loc):
    rank = []

    for abc in abcs:
        distance = getDistance(loc, (abc['latitude'], abc['longitude']))
        rank.append(tuple([abc, distance]))

    rank.sort(key=lambda x: x[1])
    return rank[:3]

def getClosestDir(abc, loc):
    angle_rad = math.atan2(abc[0]['longitude']-loc[1], abc[0]['latitude']-loc[0])
    # long = abc[0]['longitude']
    # long_0 = src[1]
    # lat = abc[0]['latitude']
    # lat_0 = src[0]
    # angle_deg = -1*math.degrees(math.atan(math.cos(lat)*math.sin(long-long_0)/(math.cos(lat_0)*math.sin(lat)-math.sin(lat_0)*math.cos(lat)*math.cos(long-long_0))))
    angle_deg = math.degrees(angle_rad)
    if -22.5 <= angle_deg < 22.5:
        return '⬆️' 
    elif 22.5 <= angle_deg < 67.5:
        return '↗️'
    elif 67.5 <= angle_deg < 112.5:
        return '➡️'
    elif 112.5 <= angle_deg < 157.5:
        return '↘️'
    elif 157.5 <= angle_deg or angle_deg < -157.5:
        return '⬇️'
    elif -157.5 <= angle_deg < -112.5:
        return '↙️'
    elif -112.5 <= angle_deg < -67.5:
        return '⬅️'
    elif -67.5 <= angle_deg < -22.5:
        return '↖️'

def log_msg(cmd):
    executable = __file__.split('/')[-1]
    log = open(__file__.replace(executable, '') + 'msg.log', 'a')
    log.write(datetime.now().strftime('%d:%m:%Y %H:%M:%S') + ': ' + str(cmd))
    log.close()

def getLocation(msg):
    return (float(msg['location']['latitude']), float(msg['location']['longitude']))

async def createHeadlessFirefoxBrowser():
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    return webdriver.Firefox(options=options)

async def getABCs():
    db = open('abcs.json', 'w')
    baseUrl = 'https://www.abcasemat.fi/fi/asemat'
    driver = await createHeadlessFirefoxBrowser()
    try:
        driver.get(baseUrl)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        stations = soup.find_all('div', {'class': 'map_station_container'})

        stations_all = [{'name': station.get('data-name').title().replace('Abc', 'ABC'),
            'latitude': float(station.get('data-latitude')),
            'longitude': float(station.get('data-longitude')),
            'url': 'https://www.abcasemat.fi' + station.get('data-url'),
            'restaurant': station.get('data-restaurant'),
            'grocery': station.get('data-grocery'),
            'extra-services': station.get('data-extra-services')}
            for station in stations]

        stations_filtered = list(filter(lambda s: s['restaurant'] == '1' or s['grocery'] == '1', stations_all))
        db.write(json.dumps(stations_filtered))
        db.close()
    except:
        print('Something went wrong')

async def handle(msg):
    global chat_id
    # These are some useful variables
    content_type, chat_type, chat_id = telepot.glance(msg)
    # Log variables
    # Check that the content type is text and not the starting
    if content_type == 'text':
        cmd = msg['text']
        try:
            print(msg['chat']['first_name'], msg['chat']['last_name'], '@' + msg['chat']['username'], cmd)
        except:
            #log_msg(msg)
            print(cmd)
        if cmd == '/kellotus':
            await kellotus()
        elif cmd == '/get_paninis':
            log_msg(msg)
            await getPaninis()
        else:
            log_msg(msg)
            return "Tuntematon komento"
    elif content_type == 'location':
        loc = getLocation(msg)
        try:
            print(msg['chat']['first_name'], msg['chat']['last_name'], '@' + msg['chat']['username'], loc)
        except:
            print(loc)
        abcs_closest = getClosest(loc)
        await postABCs(abcs_closest, loc)

async def kellotus():
    text = "Onko kaikki valmiina? Kellotus alkaa: 3"
    try:
        message = await bot.sendMessage(chat_id, text, disable_web_page_preview=True)
        for i in range(-2, 100):
            time.sleep(2)
            if i < 0:
                text = "Onko kaikki valmiina? Kellotus alkaa: " + str(abs(i))
                await bot.editMessageText(telepot.message_identifier(message), text)
            elif i == 0:
                text = "GOGOGO! 🏃🏃🏃"
                await bot.editMessageText(telepot.message_identifier(message), text)
            else:
                text = str(i)
                await bot.editMessageText(telepot.message_identifier(message), text)
    except:
        await bot.sendMessage(chat_id, 'Something went wrong...')

async def postABCs(abcs_closest, loc):
    message = ""
    R = K = '❌'
    for abc in abcs_closest:
        dir = getClosestDir(abc, loc)
        if abc[0]['restaurant'] != '': R = '✅'
        if abc[0]['grocery'] != '': K = '✅'
        message += "[{}]({}) ({}km {})\nRavintola {} Kauppa {}\n\n".format(abc[0]['name'], abc[0]['url'], abc[1], dir, R, K)
    
    message.strip()

    try:
        await bot.sendMessage(chat_id, message, disable_web_page_preview=True, parse_mode= 'Markdown')
    except:
        await bot.sendMessage(chat_id, 'Something went wrong...')

async def getPaninis():
    baseUrl = 'https://mrpanini.fi/tuotteet/'
    driver = await createHeadlessFirefoxBrowser()
    panini_list = {}
    message = "Paninivalikoima: \n\n"

    try:
        driver.get(baseUrl)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        paninis = soup.find_all('a', {'class': 'teaser__link'})
        for panini in paninis:
            name = panini.get_text()
            if name == '':
                continue
            panini_list[name] = panini.get('href')
        for panini in panini_list:
            message += '[' + panini + '](' + panini_list[panini] + ')\n'
        message.strip()

    except:
        print('Something went wrong')

    try:
        await bot.sendMessage(chat_id, message, disable_web_page_preview=True, parse_mode= 'Markdown')
    except:
        await bot.sendMessage(chat_id, 'Something went wrong...')

# Program startup
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telepot.aio.Bot(TELEGRAM_TOKEN)
loop = asyncio.get_event_loop()
loop.create_task(MessageLoop(bot, handle).run_forever())
print('Updating list of ABCs')
asyncio.run(getABCs())
print('Updated ABC database')
abc_db = open('abcs.json', 'r').read()
abcs = json.loads(abc_db)
print('Ready')

# Keep the program running
loop.run_forever()