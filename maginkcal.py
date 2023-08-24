#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This project is designed for the WaveShare 12.48" eInk display. Modifications will be needed for other displays,
especially the display drivers and how the image is being rendered on the display. Also, this is the first project that
I posted on GitHub so please go easy on me. There are still many parts of the code (especially with timezone
conversions) that are not tested comprehensively, since my calendar/events are largely based on the timezone I'm in.
There will also be work needed to adjust the calendar rendering for different screen sizes, such as modifying of the
CSS stylesheets in the "render" folder.
"""
import datetime as dt
import sys

from pytz import timezone
from gcal.gcal import GcalHelper
from render.render import RenderHelper
from power.power import PowerHelper
from run.run import RunHelper

import json
import logging


def loadConfig():
    # Basic configuration settings (user replaceable)
    configFile = open('config.json')
    global config
    config = json.load(configFile)

    global displayTZ, thresholdHours, maxEventsPerDay, isDisplayToScreen, isShutdownOnComplete
    global piSugar2Present, batteryDisplayMode, weekStartDay, dayOfWeekText, screenWidth
    global screenHeight, imageWidth, imageHeight, rotateAngle, calendars, is24hour
    global defaultView, weekStartToday, monthStartToday
    global buttonPresent, home_button_pin, view_button_pin, next_button_pin, previous_button_pin
    displayTZ = timezone(config['displayTZ']) # list of timezones - print(pytz.all_timezones)
    thresholdHours = config['thresholdHours']  # considers events updated within last 12 hours as recently updated
    maxEventsPerDay = config['maxEventsPerDay']  # limits number of events to display (remainder displayed as '+X more') (0 for dynamical)
    isDisplayToScreen = config['isDisplayToScreen']  # set to true when debugging rendering without displaying to screen
    isShutdownOnComplete = config['isShutdownOnComplete']  # set to true to conserve power, false if in debugging mode
    piSugar2Present = config['piSugar2Present'] # is PiSugar2 in the Setup available or is Power direct attached
    batteryDisplayMode = config['batteryDisplayMode']  # 0: do not show / 1: always show / 2: show when battery is low
    weekStartDay = config['weekStartDay']  # Monday = 0, Sunday = 6
    dayOfWeekText = config['dayOfWeekText'] # Monday as first item in list
    screenWidth = config['screenWidth']  # Width of E-Ink display. Default is landscape. Need to rotate image to fit.
    screenHeight = config['screenHeight']  # Height of E-Ink display. Default is landscape. Need to rotate image to fit.
    imageWidth = config['imageWidth']  # Width of image to be generated for display.
    imageHeight = config['imageHeight'] # Height of image to be generated for display.
    rotateAngle = config['rotateAngle']  # If image is rendered in portrait orientation, angle to rotate to fit screen
    calendars = config['calendars']  # Google calendar ids
    is24hour = config['is24h']  # set 24 hour time
    defaultView = config['defaultView'] # Default View ["week" or "month"]
    weekStartToday = config['weekStartToday'] # Week view Start today or on weekStartDay
    monthStartToday = config['monthStartToday'] # Month view Start today or first day of month
    buttonPresent = config['buttonPresent']  # True if buttons are present on display
    home_button_pin = config['home_button_pin']  # Pin for home button
    view_button_pin = config['view_button_pin']  # Pin for view button
    next_button_pin = config['next_button_pin']  # Pin for next event button
    previous_button_pin = config['previous_button_pin']  # Pin for previous event button

def init_logger():
    # Create and configure logger
    logging.basicConfig(filename="logfile.log", format='%(asctime)s %(levelname)s - %(message)s', filemode='a')
    global logger
    logger = logging.getLogger('maginkcal')
    logger.addHandler(logging.StreamHandler(sys.stdout))  # print logger to stdout
    logger.setLevel(logging.INFO)

def main():
    loadConfig()
    init_logger()
    if buttonPresent:
        from buttons.buttons import ButtonHelper
        buttons = ButtonHelper(config)
    run = RunHelper(config)
    date = dt.datetime.now(displayTZ).date()
    view = defaultView
    startToday= "default"
#    date = date + dt.timedelta(days=14)
    run.maginkcal(date, view, startToday)
    
    if not piSugar2Present:
        while True:
            if dt.time.minute() == 0:
                run.maginkcal(date, view, startToday)
            pass



if __name__ == "__main__":
    main()
