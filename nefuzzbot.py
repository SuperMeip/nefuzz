#!/usr/bin/python3
# -*- coding: utf-8 -*-


#Dependencies:
#########################################################
#=Telepot
#=Tweepy
#=urllib.request
#=Icalendar
#=Requests


#Imports
#########################################################
import telepot
import calendar
import json
from icalendar import Calendar
import requests
from urllib.request import urlopen
import dateutil.rrule as rrule
import re
import tweepy
import pytz
import time
from datetime import datetime, timedelta
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton
import sys

#Universal
#########################################################

bot = telepot.Bot("90380697:AAH5MQZtw_SpcqPN60yBlz57UMrP7K0oDmQ")
bot.getMe()

auth = tweepy.OAuthHandler('iuzk7MAIdF6Rssoa72nRLeH7R',
                           'YwKHP8oiN3Y8vLJsZBI21pt2YKcGngCdcOiRK7sBKSmo4K8cJp')

auth.set_access_token('3091524431-89AZUFk0ZmBoeYDWX8Rnbmeah8HR8VHu5LkeTBO',
                      'GB87nlvJTPHZAL7Ep6S2x4ft9XjFLf07l6XgY7LaTL9Jj')

api = tweepy.API(auth)

localtz = pytz.timezone("US/Eastern")

dateTest = re.compile("\d{1,2}\/\d{2}")
dateTestYear = re.compile("\d{1,2}\/\d{1,2}\/\d{4}")
distanceTest = re.compile("\d:\d\d|\d{1,3}mi")

daysOfWeek = ['•FRI', '•SAT', '•SUN', '•MON', '•TUE', '•WED', '•THU']

baseKeyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='•Search meets')],
    [KeyboardButton(text='•Get meets by:')],
    ['•Info and Links']
    ], selective=True)

getByKeyboard = ReplyKeyboardMarkup(keyboard=[
    ['•Date', '•Day'],
    ['•Week', '•Month'],
    ['•Location', '•Cancel']
], selective=True)

dayKeyboard = ReplyKeyboardMarkup(keyboard=[
    ['•FRI', '•SAT', '•SUN'],
    ['•MON', '•TUE'],
    ['•WED', '•THU']
], selective=True)

distKeyboard = ReplyKeyboardMarkup(keyboard=[
    ['20mi', '50mi', '80mi'],
    ['0:30', '1:00', '1:30' ]
], selective=True)

weekendKeyboard = ReplyKeyboardMarkup(keyboard =[
    ['This weekend', 'Next weekend'],
    ['2 Weekends from now'],
    ['3 Weeks', '4 Weeks', '5 Weeks']
], selective=True)

monthKeyboard = ReplyKeyboardMarkup(keyboard =[
    ['This month', 'Next month'],
    ['The next 30 days'],
    ['The next 60 days']
], selective=True)

locKeyboard = ReplyKeyboardMarkup(keyboard =[
    [KeyboardButton(text="•Send location",request_location=True)],
    ['•Cancel']
], selective=True)

cancelButton = ReplyKeyboardMarkup(keyboard =[
    ['•Cancel']
], selective=True)

infoBlurb = "Welcome to New England Fuzz!\n\nWe are a project devoted" \
            " to bringing free and readily available information about all" \
            " the furry goings on in New England!\n\nHere are some usefull" \
            " links to help you keep up with the New England furry community:" \
            "\n◆The Event Calendar:\n https://www.google.com/calendar/embed?src" \
            "=86krr4fvs3jjbv4nsstlj4e2v0%40group.calendar.google.com&ctz\n◆" \
            "New Enlgand Furs Map:\n https://www.google.com/maps/d/u/0/edit" \
            "?mid=zGZAfMbseBcs.k9AkKhhD1qHw\n◆The @NEFuzz Twitter:\n https://" \
            "twitter.com/NEFuzz\n◆The Events Map:\n http://chadnorwood.com/gc" \
            "m/?gc=86krr4fvs3jjbv4nsstlj4e2v0%40group.calendar.google.com\n" \
            "◆Our Website:\n http://thenewenglandfuzz.wix.com/nefuzz"


#Classes
#########################################################

class Request:
    def __init__(self, message):
        self.isGroupMessage = True if message['chat']['type'] != 'private' else False
        self.hasUserName = False
        self.chat = message['chat']['id']
        if 'username' in message['from']:
            self.userName = message['from']['username']
            self.hasUserName = True
        if not self.hasUserName:
            self.tempName = message['from']['first_name']
        self.user = message['from']['id']
        if 'text' in message:
            self.text = message['text']
        else:
            self.text = ""
        if 'location' in message:
            self.lat = message['location']['latitude']
            self.lon = message['location']['longitude']
            self.location = True
        else:
            self.location = False


class User:
    def __init__(self, chat_id):
        self.id = chat_id
        self.lastMessage = None
        self.dist = ""
        self.distSet = False


class Host:
    def __init__(self, Name, IsTwitter, IsState):
        self.name = Name
        self.isTwitter = IsTwitter
        self.isState = IsState


class Event:
    def __init__(self, Name, Time, Location, Host, Link, Notes, IsCon, Descr, UID, IsRepeat):
        self.isRepeat = IsRepeat
        self.ID = UID
        self.name = Name
        if type(Time) is datetime:
            self.time = Time.replace(tzinfo=None)
        else:
            self.time = Time
        self.location = Location
        self.host = Host
        self.link = Link
        self.notes = Notes
        self.description = Descr
        self.isCon = IsCon

        locParts = self.location.split(',')
        self.city = locParts[2].strip()
        self.state = locParts[3].strip()[:2]
        self.place = locParts[0].strip()

        trimhost = self.host.name.lower().strip()
        if (trimhost == '@rifurs') & (self.name.strip().lower() == 'ri furbowl'):
            self.fixedName = 'bowling meet'
        else:
            hostTwitters = {
                '@massfurbowl': 'meet',
                '@nhfurbowl': 'meet',
                '@microfurcon': 'meet'
            }
            self.fixedName = hostTwitters.get(trimhost, self.name)

        days = {
            0: '•MON',
            1: '•TUE',
            2: '•WED',
            3: '•THR',
            4: '•FRI',
            5: '•SAT',
            6: '•SUN'
        }
        self.dayOfWeek = days.get(self.time.weekday(), "NAN")

        if not self.isCon:
            shortTime = str(self.time.hour - (12 if self.time.hour > 12 else 0))
            mins = {
                0: "",
                30: ".5",
            }
            shortTime += mins.get(self.time.minute, ":" + str(self.time.minute))
            shortTime += "p" if self.time.hour > 12 else "a"
            self.shortTime = shortTime


    def getMessage(self, withDate=False, withDay=True):
        if not self.isCon:
            message = "♦" + ((str(self.time.month) + "/" + str(self.time.day) + " ") if withDate else "") + (
            self.dayOfWeek if withDay else "") + " at " + self.shortTime + " in " + self.city + (
                      "" if self.host.isState else ", " + self.state) + " is " + self.host.name + "'s " + self.fixedName + " at " + self.place + "! " + self.notes + " " + self.link
        else:
            message = "🎉" + ((" " + str(self.time.month) + "/" + str(
                self.time.day) + " ") if withDate else "") + "CON: " + self.name + " is this weekend in " + self.city + ', ' + self.state + ". Have fun and be safe! " + self.host.name + ". " + self.link
        return message


    def __lt__(self, other):
        if self.isCon:
            time1 = datetime(year=self.time.year, month=self.time.month, day=self.time.day)
        else:
            time1 = self.time
        if other.isCon:
            time2 = datetime(year=other.time.year, month=other.time.month, day=other.time.day)
        else:
            time2 = other.time
        return time1 < time2


class Distance:
    def __init__(self, byString, origin="", destination="", originLatLon=False, destinationLatLon=False):
        self.Failed = False
        if not byString:
            self.time = True
            self.dist = True
            spaces = [', ', ' ,', ' ', ',']
            for i in spaces:
                if not originLatLon:
                    origin = origin.replace(i, '+')
                if not destinationLatLon:
                    destination = destination.replace(i, '+')
            url = "https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins=" + origin + "&destinations=" + destination + "&key=AIzaSyAVHaRFclrSmQusTzLrdYa_CQrJdLeFxcU"
            distJson = requests.get(url).json()
            if distJson['status'] == 'INVALID_REQUEST':
                self.Failed = True
            else:
                if distJson['rows'][0]['elements'][0]['status'] != 'OK':
                    self.Failed = True
                else:
                    disttIME = distJson['rows'][0]['elements'][0]['duration']['text']
                    distMi = distJson['rows'][0]['elements'][0]['distance']['text']
                    self.origin = distJson['origin_addresses'][0]

                    miParts = distMi.split()
                    self.miles = round(float(miParts[0]))

                    tiParts = disttIME.split()
                    if len(tiParts) == 4:
                        self.hours = int(tiParts[0])
                        self.minuets = int(tiParts[2])
                    else:
                        self.minuets = int(tiParts[0])
                        self.hours = 0
        else:
            if ':' in byString:
                self.time = True
                self.dist = False
                parts = byString.split(':')
                self.hours = int(parts[0])
                self.minuets = int(parts[1])
            else:
                self.time = False
                self.dist = True
                mi = byString[:-2]
                self.miles = int(mi)

    def toStr(self, inMiles=True, inTime=True):
        if self.Failed:
            return "Failed!"
        string = ""
        if self.dist & inMiles:
            string += str(self.miles) + " miles" + (", or " if (inTime & self.time) else "")
        if self.time & inTime:
            string += ((str(self.hours) + " hour" + (
            "s" if self.hours != 1 else "") + " and ") if self.hours != 0 else "") + str(self.minuets) + " minuets"
        return string

    def isGreaterThan(self, otherDist, inMiles=True, inTime=True):
        if self.Failed or otherDist.Failed:
            return False
        time = dist = True
        if inMiles:
            if (otherDist.dist == False) or (self.dist == False):
                return False
            else:
                dist = self.miles > otherDist.miles
        if inTime:
            if (otherDist.time == False) or (self.time == False):
                return False
            else:
                if self.hours > otherDist.hours:
                    time = True
                elif self.hours < otherDist.hours:
                    return False
                elif self.hours == otherDist.hours:
                    time = self.minuets > otherDist.minuets
        return time & dist

    def isEqualOrGreaterThan(self, otherDist, inMiles=True, inTime=True):
        if self.Failed or otherDist.Failed:
            return False
        time = dist = True
        if inMiles:
            if (otherDist.dist == False) or (self.dist == False):
                return False
            else:
                dist = self.miles >= otherDist.miles
        if inTime:
            if (otherDist.time == False) or (self.time == False):
                return False
            else:
                if self.hours > otherDist.hours:
                    time = True
                elif self.hours < otherDist.hours:
                    return False
                elif self.hours == otherDist.hours:
                    time = self.minuets >= otherDist.minuets
        return time & dist


#Functions
#########################################################

def handler(m):
#####Set up variables
    failed = False
    failMessage = ""
    message = Request(m)
    print("Message recieved at " + str(datetime.now()) + "\n  User: " + str(message.user) + (" : @" + message.userName if message.hasUserName else "") +
          (", Sent in group: " + str(message.chat) if message.isGroupMessage else "") + '\n\t' + "Message: " + (message.text if not message.location else "*Location sent"))


#####Get user, or add user to users list
    if message.user not in Users:
        Users[message.user] = User(message.user)
        Users[message.user].lastMessage = message.text
        print("\tNew user registered")
        bot.sendMessage(message.chat, tryUserName(message) + "Welcome to NEFuzz bot! Press a button to continue", reply_markup=baseKeyboard)
        return
    print("\tLast message: " + Users[message.user].lastMessage)


#####Group Catch
    if message.isGroupMessage & (not message.hasUserName):
        bot.sendMessage(message.chat, message.tempName + ", you must have an @ username to use this bot in a group chat", reply_markup=baseKeyboard)
        Users[message.user].lastMessage = '•Cancel'
        return


#####Cancel
    if (message.text == '/cancel') or (message.text == '•Cancel') or (message.text == '/start@NEFuzzBot') or (message.text == '/start') or (message.text == '/cancel@NEFuzzBot'):
        Users[message.user].distSet = False
        bot.sendMessage(message.chat, tryUserName(message) + "Welcome to NEFuzz bot! Press a button to continue", reply_markup=baseKeyboard)
        Users[message.user].lastMessage = 'Cancel'


#####Check Events
    if message.text == '/check':
        checkWeeklyEvents(message.user)


#####Push first events to file
    if message.text == '/firstEventPush':
        print('worked')
        pushToPrevious()


#####test Changed Meets
    if message.text == '/testChanges':
        postMeetChanges()

#####Post Events
    if message.text == '/post twitter EPK':
        post(True, False)
    if message.text == '/post telegram EPK':
        post(False, True)
    if message.text == '/post both EPK':
        post()


#####Tweet
    if '/tweetEPK' in message.text:
        sendTweet(message.text[9:])


#####Postpone Events
    global  postTw
    global postTe
    if message.text == '/postpone twitter':
        postTw = False
    if message.text == '/postpone telegram':
        postTe = False
    if message.text == '/reset postpone':
        postTw = True
        postTe = True


#####Info
    if message.text == '•Info and Links':
        bot.sendMessage(message.chat, tryUserName(message) + infoBlurb, reply_markup=baseKeyboard)


#####Search
#####Stage 1 : pressed button
    elif message.text == '•Search meets':
        bot.sendMessage(message.chat, tryUserName(message) + "Enter a specific phrase to search in the events happening in the next 60 days. Keep in mind this is specific", reply_markup=cancelButton)
#####Stage 2 : entered term
    elif Users[message.user].lastMessage == '•Search meets':
        bot.sendMessage(message.chat, tryUserName(message) + "Searching for '" + message.text + "' in all meets, please wait this may take a moment.", reply_markup=baseKeyboard)
        bot.sendMessage(message.chat, tryUserName(message) + eventBySearch(message.text), reply_markup=baseKeyboard)


#####GetBy
#####Stage 1 : pressed button
    elif message.text == '•Get meets by:':
        bot.sendMessage(message.chat, tryUserName(message) + "Use the options below to search for and obtain lists of meets in different ways", reply_markup=getByKeyboard)


#####Get by location
#####Stage 1 : pressed button
    elif message.text == '•Location':
        bot.sendMessage(message.chat, tryUserName(message) + "Press one of the buttons below or send a distance in miles or drive time in one of the following formats: \n#mi as miles\n#:## as hours:minuets", reply_markup=distKeyboard)
#####Stage 2 : pressed/sent distance
    elif re.search(distanceTest, message.text):
        if Users[message.user].lastMessage == '•Location':
            distance = re.search(distanceTest, message.text).group(0)
            Users[message.user].dist = distance
            Users[message.user].distSet = True
            bot.sendMessage(message.chat, tryUserName(message) + "Distance set to: " + distance + ". Please enter a location to search around:\n examples:\n Worcester,MA\n ", reply_markup=locKeyboard)
#####Stage 3 : Sent origin
    elif Users[message.user].distSet:
        if message.location:
            loca = (str(message.lat) + "," + str(message.lon))
            bot.sendMessage(message.chat, tryUserName(message) + "Please wait, searching for meets. This may take a moment.", reply_markup=baseKeyboard)
            bot.sendMessage(message.chat, tryUserName(message) + eventByLocation(loca, Users[message.user].dist, True), reply_markup=baseKeyboard)
            Users[message.user].distSet = False
        else:
            bot.sendMessage(message.chat, tryUserName(message) + "Please wait, searching for meets. This may take a moment.", reply_markup=baseKeyboard)
            reply = eventByLocation(message.text, Users[message.user].dist)
            Users[message.user].distSet = False
            bot.sendMessage(message.chat, tryUserName(message) + reply, reply_markup=baseKeyboard)
#####Stage 3 : Sent location:
    elif message.location:
        loc = (str(message.lat) + "," + str(message.lon))
        bot.sendMessage(message.chat, tryUserName(message) + "Please wait, searching for meets. This may take a moment.", reply_markup=baseKeyboard)
        bot.sendMessage(message.chat, tryUserName(message) + eventByLocation(loc, Users[message.user].dist, True), reply_markup=baseKeyboard)
        Users[message.user].distSet = False


#####Get By Date
#####Stage 1 : button pressed
    elif message.text == '•Date':
        bot.sendMessage(message.chat, tryUserName(message) + "Enter a date in MM/DD or MM/DD/YYYY format and we will send a list of all the events on that day: ", reply_markup=baseKeyboard)
#####Stage 2 : entered date
    elif re.search(dateTest, message.text):
        if re.search(dateTestYear, message.text):
            if Users[message.user].lastMessage == '•Date':
                try:
                    date = datetime.strptime(message.text, "%m/%d/%Y")
                    bot.sendMessage(message.chat, tryUserName(message) + eventsByDate(date.date()), reply_markup=baseKeyboard)
                except ValueError:
                    failed = True
                    failMessage = "Invalid date, please try again"
        else:
            if Users[message.user].lastMessage == '•Date':
                try:
                    date = datetime.strptime(message.text + '/' + str(datetime.now().year), "%m/%d/%Y")
                    bot.sendMessage(message.chat, tryUserName(message) + eventsByDate(date.date()), reply_markup=baseKeyboard)
                except ValueError:
                    failed = True
                    failMessage = "Invalid date, please try again"


#####Get by day
#####Stage 1 : button pressed
    elif message.text == '•Day':
        bot.sendMessage(message.chat, tryUserName(message) + "Choose the upcoming day to check it for meets:", reply_markup=dayKeyboard)
#####Stage 2 : picked day
    elif message.text in daysOfWeek:
        if Users[message.user].lastMessage == '•Day':
            bot.sendMessage(message.chat, tryUserName(message) + eventByDay(message.text), reply_markup=baseKeyboard)


#####Get by Week
#####Stage 1 : button pressed
    elif message.text == '•Week':
        bot.sendMessage(message.chat, "Get meets by the weekend!\n To check what meets are on this or an upcoming weekend, select one of the following options: ", reply_markup=weekendKeyboard)
#####Stage 2 : weeks sent
    elif message.text == 'Next weekend':
        if Users[message.user].lastMessage == '•Week':
            bot.sendMessage(message.chat, tryUserName(message) + eventByWeekend(1), reply_markup=baseKeyboard)
    elif message.text == 'This weekend':
        if Users[message.user].lastMessage == '•Week':
            bot.sendMessage(message.chat, tryUserName(message) + eventByWeekend(0), reply_markup=baseKeyboard)
    elif message.text == '2 Weekends from now':
        if Users[message.user].lastMessage == '•Week':
            bot.sendMessage(message.chat, tryUserName(message) + eventByWeekend(2), reply_markup=baseKeyboard)
    elif 'Weeks' in message.text:
        if Users[message.user].lastMessage == '•Week':
            bot.sendMessage(message.chat, tryUserName(message) + eventByWeekend(int(message.text.split()[0])), reply_markup=baseKeyboard)


#####Get by Month
#####Stage 1 : button pressed
    elif message.text == '•Month':
        bot.sendMessage(message.chat, "Get meets by the month!\n To check what meets are in this or an upcoming month, select one of the following options: ", reply_markup=monthKeyboard)
#####Stage 2 : weeks sent
    elif message.text == 'Next month':
        if Users[message.user].lastMessage == '•Month':
            bot.sendMessage(message.chat, tryUserName(message) + eventByMonth(1), reply_markup=baseKeyboard)
    elif message.text == 'This month':
        if Users[message.user].lastMessage == '•Month':
            bot.sendMessage(message.chat, tryUserName(message) + eventByMonth(0), reply_markup=baseKeyboard)
    elif 'The next ' in message.text:
        if Users[message.user].lastMessage == '•Month':
            bot.sendMessage(message.chat, tryUserName(message) + eventByMonth(int(message.text.split()[2]), True), reply_markup=baseKeyboard)


#####End, Fail message or set last.
    if not failed:
        Users[message.user].lastMessage = message.text
    else:
        bot.sendMessage(message.chat, tryUserName(message) + failMessage, reply_markup=baseKeyboard)


def eventsByDate(date):
    events = getEvents(date,1)
    message = "Events occuring on " + str(date.month) + "/" + str(date.day) + "/" + str(date.year) + ":\n\n"
    if len(events)>0:
        for e in events:
            message += e.getMessage(False, False) + "\n\n"
    else:
        message = "There are NO events occuring on " + str(date.month) + "/" + str(date.day) + "/" + str(date.year) + "."
    return message


def eventByDay(day):
    events = getEvents(today,7)
    message = "Events occuring on this upcoming " + day + ":\n\n"
    event = False
    if len(events) > 0:
        for e in events:
            if e.dayOfWeek == day:
                message += e.getMessage(False, False) + "\n\n"
                event = True
    if not event:
        message = "There are NO events occuring on this upcoming " + day + "."
    return message


def eventByWeekend(weeks):
    date = getMonday(today + timedelta(days=(7*weeks)))
    events = getEvents(date,7)
    message = "Events occuring on the week of " + str(date.month) + "/" + str(date.day) + "/" + str(date.year) + ":\n\n"
    if len(events) > 0:
        for e in events:
            message += e.getMessage(False, True) + "\n\n"
    else:
        message = "There are NO events occuring the week of " + str(date.month) + "/" + str(date.day) + "/" + str(date.year) + "."
    return message


def eventByMonth(days, span=False):
    events = []
    if not span:
        if days == 0:
            thisMonthDays = calendar.monthrange(today.year,today.month)[1] - today.day
            events = getEvents(today, thisMonthDays)
        elif days == 1:
            start = today.replace(month=today.month+1,day=1)
            thatMonthDays = calendar.monthrange(start.year,start.month)[1]
            events = getEvents(start, thatMonthDays)
    else:
        events = getEvents(today, days)
    message = "Events occuring within the selected timeframe:\n\n"
    if len(events) > 0:
        for e in events:
            message += e.getMessage(True, True) + "\n\n"
    else:
        message = "There are NO events occuring within the desired timeframe."
    return message


def getMonday(date):
    if date.weekday() == 6:
        monday = date + timedelta(days=1)
    else:
        monday = date - timedelta(days=date.weekday())
    return monday


def eventByLocation(location, distance, isLocation=False):
    desiredDistance = Distance(distance)
    events = getEvents(today,60)
    message = "Events occuring within " + desiredDistance.toStr(True,True) + " of " + (location if not isLocation else "you") + " in the next 60 days:\n\n"
    event = False
    for e in events:
        eventDistance = Distance(False,location, e.city + " " + e.state, isLocation)
        if desiredDistance.isEqualOrGreaterThan(eventDistance,desiredDistance.dist,desiredDistance.time):
            message += e.getMessage(True, True) + " Distance: " + eventDistance.toStr(True,True) + "\n\n"
            event = True
    if not event:
        message = "There are NO events occuring within " + desiredDistance.toStr(True,True) + " of " + location if not isLocation else "you" + " in the next 60 days."
    return message


def eventBySearch(text):
    events = getEvents(today,60)
    message = "Events found containing, '" + text + "', in their description in the next 60 days:\n\n"
    event = False
    for e in events:
        if re.search(text.lower(),(e.location + " " + e.description + " " + e.name + " " + e.host.name).lower()):
            message += e.getMessage(True, True) + "\n\n"
            event = True
    if not event:
        message = "There were NO events found containing, '" + text + "', in their descriptions in the next 60 days."
    return message


def checkWeeklyEvents(userID, userID2=False):
    events = getEvents(today, 7)
    Message = "Make sure everything is set for the automated message on WED at 3p! : \n\n"
    for event in events:
        eventPost = event.getMessage()
        if len(eventPost) <= 140:
            Message += str(len(eventPost)) + " : " + eventPost + '\n\n'
        else:
            Message += "!" + str(len(eventPost)) + " : " + eventPost + '\n\n'
    bot.sendMessage(userID, Message, reply_markup=baseKeyboard)
    if userID2:
        bot.sendMessage(userID2, Message, reply_markup=baseKeyboard)


def Shorten(long_url):

    result = None
    f = urlopen("http://tinyurl.com/api-create.php?url={0}".format(
        long_url))
    try:
        result = f.read()
    finally:
        f.close()

    if isinstance(result, bytes):
        return result.decode('utf8')
    else:
        return result


def getEvents(date=True, days=1, fromPrevious=False):
    eventList = []
    if not fromPrevious:
        ics = requests.get("https://calendar.google.com/"
            "calendar/ical/86krr4fvs3jjbv4nsstlj4e2v"
            "0%40group.calendar.google.com/public/ba"
            "sic.ics")
        cal = Calendar.from_ical(ics.content)
    else:
        ics = open("previous_events.ics", 'rb').read()
        cal = Calendar.from_ical(ics)
    for e in cal.walk('vevent'):
        eventTime = e.get('dtstart')
        if type(eventTime) != datetime:
            eventTime = eventTime.dt
        if type(eventTime) == datetime:
            timeAdjust = -4 if eventTime.utcoffset() / timedelta(hours=1) != -4.0 else 0
            eventTime = eventTime + timedelta(hours=timeAdjust)
        rr = e.get('rrule')
        if type(eventTime) != type(date):
            eventTime = eventTime.date()
        if str(rr) != "None":
            if 'count' not in rr:
                if 'until' not in rr:
                    addRecurringEvent(e, eventList, date, days)
        if (eventTime >= date) & (eventTime < (date + timedelta(days=days))):
            addNormalEvent(e, eventList)
    eventList.sort()
    return eventList


def addNormalEvent(event, eList):
    for e in eList:
        if str(e.name) == str(event.get('summary')):
            return
    newEvent = event
    eventTime = newEvent.get('dtstart')
    if type(eventTime) != datetime:
        eventTime = eventTime.dt
    if type(eventTime) == datetime:
        timeAdjust = -4 if eventTime.utcoffset() / timedelta(hours=1) != -4.0 else 0
        eventTime = eventTime + timedelta(hours=timeAdjust)
    newEvent['dtstart'] = eventTime
    addEvent(newEvent, eList, False)


def addRecurringEvent(event, eList, day, days):
    for e in eList:
        if str(e.name) == str(event.get('summary')):
            return
    icalString = event.get('rrule').to_ical()
    ics = icalString.decode().split("'")
    eventTime = event.get('dtstart').dt
    startTime = day #+ timedelta(days=1) # - (timedelta(days=31) if 'MONTHLY' in ics[0] else timedelta(days=7))
    events = list(rrule.rrulestr(ics[0] + ";COUNT=20", dtstart=startTime))
    for ev in events:
        if ev.date() <= (day + timedelta(days=days-1)):
            nextEvent = event
            newDateTime = ev.replace(hour=eventTime.hour, minute=eventTime.minute)
            nextEvent['dtstart'] = newDateTime
            addEvent(nextEvent, eList, True)
    return


def addEvent(event, eList, isRepeat):
    eventLoc = event.get('location')
    descParts = event.get('description').split('\n')
    desc = event.get('description')
    link = Shorten(descParts[0])
    host = Host(descParts[1], True if descParts[1][:1] == '@' else False, checkState(descParts[1]))
    notes = descParts[2] if len(descParts) > 2 else ""
    isCon = False if notes != "CON!" else True
    eventTime = event.get('dtstart')
    location = eventLoc
    uid = event.get('uid')
    name = event.get('summary')
    newEvent = Event(name, eventTime, location, host, link, notes, isCon, desc, uid, isRepeat)
    eList.append(newEvent)
    return


def checkState(name):
    lowerName = name.lower().strip()
    states = {
        '@mafurs': True,
        '@rifurs': True,
        '@mainefurs': True,
        '@vermontfurs': True,
        '@ctfurs': True,
        '@nhfurs': True,
        '@nhfurbowl': True,
        '@massfurbowl': True,
        '@microfurcon': True
    }
    return states.get(lowerName, False)


def TwitterPostEvents(events):

    rootStatus = api.update_status("📢 It's time to announce this weekend's meets!")

    print(str(len(events)))

    for event in events:
        eventPost = event.getMessage()
        if len(eventPost) <= 140:
            print(str(len(eventPost)) + " : " + eventPost)
            api.update_status(eventPost, rootStatus.id)
        else:
            print("!" + str(len(eventPost)) + " : " + eventPost)


def TelegramPostEvents(events):
    Message = "📢Time to announce meets and events for this weekend!\n\n"

    for event in events:
        Message += event.getMessage() + '\n\n'

    print(Message)
    bot.sendMessage('@NEFuzz', Message)


def post(twitter = True, telegram = True):
    events = getEvents(today, 7)
    if twitter:
        TwitterPostEvents(events)
    if telegram:
        TelegramPostEvents(events)


def compareNewEvents(oldMeets, newMeets):
    meetAnnouncments = []
    meetsToAnnounce = []
    meetsToCancel = []
    timeChanges = []

    for newEvent in newMeets:
        if not newEvent.isRepeat:
            eventFound = False
            for oldEvent in oldMeets:
                if newEvent.ID == oldEvent.ID:
                    eventFound = True
                    if newEvent.time != oldEvent.time:
                        timeChanges.append(newEvent)
            if not eventFound:
                meetsToAnnounce.append(newEvent)

    for oldEvent in oldMeets:
        eventFound = False
        for newEvent in newMeets:
            if newEvent.ID == oldEvent.ID:
                eventFound = True
        if not eventFound:
            meetsToCancel.append(oldEvent)

    meetAnnouncments.append(meetsToAnnounce)
    meetAnnouncments.append(timeChanges)
    meetAnnouncments.append(meetsToCancel)
    return meetAnnouncments


def postMeetChanges():
    newEventList = getEvents(today, 60)
    previousEvents = pullFromPrevious()
    announcementLists = compareNewEvents(previousEvents, newEventList)
    if (len(announcementLists[0]) + len(announcementLists[1]) + len(announcementLists[2])) < 1:
        print("No Changes on " + str(datetime.now()))
        return
    telegramMessage = "📣Time for some announcments!\n\n"
    twitterRoot = api.update_status(telegramMessage)

    if len(announcementLists[0]) > 0:
        telegramMessage += "\tNew Meets Added:\n\n"

    for event in announcementLists[0]:
        text = event.name + " will be hosted by " + event.host.name + " on " + event.dayOfWeek + " " + str(event.time.month) + "/" + str(event.time.day) + " at " + event.shortTime + " in " + event.city + ", " + event.state + ". " + event.link
        if len("➕: " + text) <= 140:
            api.update_status("➕: " + text, twitterRoot)
            #bot.sendMessage(50191149,"Tweet good\n" + str(len("➕: " + text)) + " characters\n➕: " + text, reply_markup=baseKeyboard)
        else:
            bot.sendMessage(50191149,"Tweet not sent!\n" + str(len("➕: " + text)) + " characters\n➕: " + text, reply_markup=baseKeyboard)
        telegramMessage += "➕" + text + '\n\n'

    if len(announcementLists[1]) > 0:
        telegramMessage += "\tMeet Times Changed:\n\n"

    for event in announcementLists[1]:
        text = event.name + " in " + event.city + ", " + event.state + " has been moved to " + event.dayOfWeek + " " + str(event.time.month) + "/" + str(event.time.day) + " at " + event.shortTime +  ". " + event.link
        if len("🕒: " + text) <= 140:
            api.update_status("🕒: " + text, twitterRoot)
            #bot.sendMessage(50191149,"Tweet good!\n" + str(len("🕒: " + text)) + " characters\n🕒: " + text, reply_markup=baseKeyboard)
        else:
            bot.sendMessage(50191149,"Tweet not sent!\n" + str(len("🕒: " + text)) + " characters\n🕒: " + text, reply_markup=baseKeyboard)
        telegramMessage += "🕒" + text + '\n\n'

    if len(announcementLists[2]) > 0:
        telegramMessage += "\tMeets Canceled:\n\n"

    for event in announcementLists[2]:
        text = event.name + " in " + event.city + ", " + event.state + " on " + event.dayOfWeek + " " + str(event.time.month) + "/" + str(event.time.day) + " at " + event.shortTime +  " has been canceled"
        if len("🚫: " + text) <= 140:
            api.update_status("🚫: " + text, twitterRoot)
            #bot.sendMessage(50191149,"Tweet good!\n" + str(len("🚫: " + text)) + " characters\n🚫: " + text, reply_markup=baseKeyboard)
        else:
            bot.sendMessage(50191149,"Tweet not sent!\n" + str(len("🚫: " + text)) + " characters\n🚫: " + text, reply_markup=baseKeyboard)
        telegramMessage += "🚫" + text + '\n\n'

    bot.sendMessage('@NEFuzz', telegramMessage, reply_markup=baseKeyboard)
    pushToPrevious()


def pullFromPrevious():
    return getEvents(today, 60, True)


def pushToPrevious():
    ics = requests.get("https://calendar.google.com/"
            "calendar/ical/86krr4fvs3jjbv4nsstlj4e2v"
            "0%40group.calendar.google.com/public/ba"
            "sic.ics")
    cal = Calendar.from_ical(ics.content)
    print("Push for first time at :" + str(datetime.now()))
    file = open('previous_events.ics', 'wb')
    file.write(cal.to_ical())


def tryUserName(message):
    if not message.isGroupMessage:
        return ""
    else:
        return '@' + message.userName + '\n'


def sendTweet(text):
    api.update_status(text)


def main():
    bot.message_loop(handler)
    while True:
        global today
        today = datetime.now(localtz).date() + timedelta(days=0)
        now = datetime.now()
        if (now.weekday() == 2) & (now.hour == 15):
            post(postTw, postTe)
            print("Posted at: ")
        elif (now.weekday() == 1) & (now.hour == 12):
            checkWeeklyEvents(50191149,135591396)
            print("Sent test message at: ")
        else:
            print("No post at: ")
        print(str(now))
        time.sleep(3600)
        postMeetChanges()


#Tests
#########################################################
postTw = True
postTe = True
today = datetime.now(localtz).date() + timedelta(days=0)
Users = {}
if __name__ == '__main__':
    main()

