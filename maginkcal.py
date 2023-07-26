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
import json
import logging


def setCalStartEndTime(date, range, startToday, weekStartDay):
    if startToday:
        if range == "week":
            StartDate = date - dt.timedelta(days=((date.weekday() + (7 - weekStartDay)) % 7))
            EndDate = StartDate + dt.timedelta(days=(6))
            days = (EndDate - StartDate).days  + 1
            return {"StartDate": StartDate , "EndDate": EndDate, "Range": days}
        elif range == "month":
            StartDate = date - dt.timedelta(days=((date.weekday() + (7 - weekStartDay)) % 7))
            EndDate = StartDate + dt.timedelta(days=(5 * 7 - 1))
            days = (EndDate - StartDate).days  + 1
            return {"StartDate": StartDate , "EndDate": EndDate, "Range": days}
        else:
            return
    else:
        if range == "week":
            days_until_week_start = (date.weekday()- weekStartDay) % 7
            StartDate = date - dt.timedelta(days=(0 + days_until_week_start))
            EndDate = StartDate + dt.timedelta(days=(6))
            days = (EndDate - StartDate).days  + 1
            return {"StartDate": StartDate , "EndDate": EndDate, "Range": days}
        elif range == "month":
            first_of_month = date.replace(day=1)
            last_of_month = date.replace(day=1, month=date.month + 1) - dt.timedelta(days=1)
            days_until_week_start = (weekStartDay - first_of_month.weekday()) % 7
            if days_until_week_start == 0:
                days_until_week_start = 7
            StartDate = first_of_month - dt.timedelta(days=(7 - days_until_week_start))
            days_until_week_end = (weekStartDay - last_of_month.weekday()) % 7
            if days_until_week_end == 0:
                days_until_week_end = 7
            EndDate = last_of_month + dt.timedelta(days=days_until_week_end - 1)
            days = (EndDate - StartDate).days  + 1
            return {"StartDate": StartDate , "EndDate": EndDate, "Range": days}
        else:
            return

def main():
    # Basic configuration settings (user replaceable)
    configFile = open('config.json')
    config = json.load(configFile)

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

    # Create and configure logger
    logging.basicConfig(filename="logfile.log", format='%(asctime)s %(levelname)s - %(message)s', filemode='a')
    logger = logging.getLogger('maginkcal')
    logger.addHandler(logging.StreamHandler(sys.stdout))  # print logger to stdout
    logger.setLevel(logging.INFO)
    logger.info("Starting daily calendar update")

    try:
        # Establish current date and time information
        # Note: For Python datetime.weekday() - Monday = 0, Sunday = 6
        # For this implementation, each week starts on a Sunday and the calendar begins on the nearest elapsed Sunday
        # The calendar will also display 5 weeks of events to cover the upcoming month, ending on a Saturday
        if piSugar2Present:
            powerService = PowerHelper()
            powerService.sync_time()
            currBatteryLevel = powerService.get_battery()
            logger.info('Battery level at start: {:.3f}'.format(currBatteryLevel))
        else:
            logger.info('no piSugar2 present set Dummy values')
            currBatteryLevel = 100

        currDatetime = dt.datetime.now(displayTZ)
        logger.info("Time synchronised to {}".format(currDatetime))
        currDate = currDatetime.date()
        #calRange = setCalStartEndTime(currDate, defaultView, weekStartToday, weekStartDay)
        date = currDate.replace(month=2, year=2027 )
        calRange = setCalStartEndTime(date, "month", False , weekStartDay)
        calStartDatetime = displayTZ.localize(dt.datetime.combine(calRange['StartDate'], dt.datetime.min.time()))
        calEndDatetime = displayTZ.localize(dt.datetime.combine(calRange['EndDate'], dt.datetime.max.time()))

        # Using Google Calendar to retrieve all events within start and end date (inclusive)
        start = dt.datetime.now()
        gcalService = GcalHelper()
        eventList = gcalService.retrieve_events(calendars, calStartDatetime, calEndDatetime, displayTZ, thresholdHours)
        #eventList = []
        logger.info("Calendar events retrieved in " + str(dt.datetime.now() - start))

        # Populate dictionary with information to be rendered on e-ink display
        calDict = {'events': eventList, 'calStartDate': calRange['StartDate'], 'today': currDate, 'lastRefresh': currDatetime,
                   'batteryLevel': currBatteryLevel, 'batteryDisplayMode': batteryDisplayMode,
                   'dayOfWeekText': dayOfWeekText, 'weekStartDay': weekStartDay, 'maxEventsPerDay': maxEventsPerDay,
                   'is24hour': is24hour, 'calRange': calRange['Range'], 'referenceDay': date}

        renderService = RenderHelper(imageWidth, imageHeight, rotateAngle)
        calBlackImage, calRedImage = renderService.process_inputs(calDict)

        if isDisplayToScreen:
            from display.display import DisplayHelper
            displayService = DisplayHelper(screenWidth, screenHeight)
            if currDate.weekday() == weekStartDay:
                # calibrate display once a week to prevent ghosting
                displayService.calibrate(cycles=0)  # to calibrate in production
            displayService.update(calBlackImage, calRedImage)
            displayService.sleep()
        if piSugar2Present:
            currBatteryLevel = powerService.get_battery()
            logger.info('Battery level at end: {:.3f}'.format(currBatteryLevel))

    except Exception as e:
        logger.error(e)

    logger.info("Completed daily calendar update")

    logger.info("Checking if configured to shutdown safely - Current hour: {}".format(currDatetime.hour))
    if isShutdownOnComplete:
        # implementing a failsafe so that we don't shutdown when debugging
        # checking if it's 6am in the morning, which is the time I've set PiSugar to wake and refresh the calendar
        # if it is 6am, shutdown the RPi. if not 6am, assume I'm debugging the code, so do not shutdown
        if currDatetime.hour == 6:
            logger.info("Shutting down safely.")
            import os
            os.system("sudo shutdown -h now")


if __name__ == "__main__":
    main()
