#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script essentially generates a HTML file of the calendar I wish to display. It then fires up a headless Chrome
instance, sized to the resolution of the eInk display and takes a screenshot. This screenshot will then be processed
to extract the grayscale and red portions, which are then sent to the eInk display for updating.

This might sound like a convoluted way to generate the calendar, but I'm doing so mainly because (i) it's easier to
format the calendar exactly the way I want it using HTML/CSS, and (ii) I can better delink the generation of the
calendar and refreshing of the eInk display. In the future, I might choose to generate the calendar on a separate
RPi device, while using a ESP32 or PiZero purely to just retrieve the image from a file host and update the screen.
"""

from time import sleep
from datetime import timedelta
import pathlib
import logging
import calendar
from operator import itemgetter
import imgkit
import cv2
import numpy as np
from PIL import Image


class RenderHelper:

    def __init__(self, width, height, angle):
        self.logger = logging.getLogger('maginkcal')
        self.currPath = str(pathlib.Path(__file__).parent.absolute())
        self.htmlFile = 'file://' + self.currPath + '/calendar.html'
        self.imageWidth = width
        self.imageHeight = height
        if angle == 0:
            self.rotate = False
        elif angle == 90:
            self.rotate = True
            self.rotateAngle = cv2.ROTATE_90_CLOCKWISE
        elif angle == 180:
            self.rotate = True
            self.rotateAngle = cv2.ROTATE_180
        elif angle == 270:
            self.rotate = True
            self.rotateAngle = cv2.ROTATE_90_COUNTERCLOCKWISE


    def render_image(self):
        options = {
            'format': 'png',
            'encoding': "UTF-8",
            'height': self.imageHeight,
            'width': self.imageWidth,
            'enable-local-file-access': None
        }

        imgkit.from_file(self.currPath + '/calendar.html', self.currPath + '/calendar.png', options=options)

        self.logger.info('Screenshot captured and saved to file.')

        img = cv2.imread(self.currPath + '/calendar.png', cv2.IMREAD_UNCHANGED)  # get image

        #mask
        lower_red = np.array([0,0,1,255])
        upper_red = np.array([0,0,255,255])
        mask = cv2.inRange(img, lower_red, upper_red)

        # set my output img to zero everywhere except my mask
        redimg = img.copy()
        redimg[np.where(mask==0)] = 0

        blackimg = img[:,:,2]

        if self.rotate:
            redimg = cv2.rotate(redimg, self.rotateAngle)
            blackimg = cv2.rotate(blackimg, self.rotateAngle)
        #save channels for debugging
        cv2.imwrite(self.currPath + '/red-channel.png',redimg) 
        cv2.imwrite(self.currPath + '/black-channel.png',blackimg) 

        blackimg = Image.open(self.currPath + '/black-channel.png')
        redimg = Image.open(self.currPath + '/red-channel.png')	

        self.logger.info('Image colours processed. Extracted grayscale and red images.')
        return blackimg, redimg

        
    def get_day_in_cal(self, startDate, eventDate):
        delta = eventDate - startDate
        return delta.days

    def get_short_time(self, datetimeObj, is24hour=False):
        datetime_str = ''
        if is24hour:
            datetime_str = '{}:{:02d}'.format(datetimeObj.hour, datetimeObj.minute)
        else:
            if datetimeObj.minute > 0:
                datetime_str = '.{:02d}'.format(datetimeObj.minute)

            if datetimeObj.hour == 0:
                datetime_str = '12{}am'.format(datetime_str)
            elif datetimeObj.hour == 12:
                datetime_str = '12{}pm'.format(datetime_str)
            elif datetimeObj.hour > 12:
                datetime_str = '{}{}pm'.format(str(datetimeObj.hour % 12), datetime_str)
            else:
                datetime_str = '{}{}am'.format(str(datetimeObj.hour), datetime_str)
        return datetime_str

    def process_inputs(self, calDict):
        # calDict = {'events': eventList, 'calStartDate': calStartDate, 'today': currDate, 'lastRefresh': currDatetime, 'batteryLevel': batteryLevel}
        # first setup list to represent the 5 weeks in our calendar
        calList = []
        for i in range(calDict['calRange']):
            calList.append([])

        # retrieve calendar configuration
        maxEventsPerDay = calDict['maxEventsPerDay']
        batteryDisplayMode = calDict['batteryDisplayMode']
        dayOfWeekText = calDict['dayOfWeekText']
        weekStartDay = calDict['weekStartDay']
        is24hour = calDict['is24hour']
        
        # set week count
        weekCount = round(calDict['calRange'] / 7)

        # for each item in the eventList, add them to the relevant day in our calendar list
        for event in calDict['events']:
            idx = self.get_day_in_cal(calDict['calStartDate'], event['startDatetime'].date())
            if idx >= 0:
                calList[idx].append(event)
            if event['isMultiday']:
                idxEnd = self.get_day_in_cal(calDict['calStartDate'], event['endDatetime'].date())
                if idxEnd < len(calList):
                    calList[idxEnd].append(event)
                if weekCount == 1:
                    for idxN in range(idx + 1 , idxEnd):
                        if idxN < len(calList):
                            calList[idxN].append(event)


        # Read html template
        with open(self.currPath + '/calendar_template.html', 'r') as file:
            calendar_template = file.read()

        # Insert month header
        month_name = calendar.month_name[calDict['referenceDay'].month]

        # Insert battery icon
        # batteryDisplayMode - 0: do not show / 1: always show / 2: show when battery is low
        battLevel = calDict['batteryLevel']

        if batteryDisplayMode == 0:
            battText = 'batteryHide'
        elif batteryDisplayMode == 1:
            if battLevel >= 80:
                battText = 'battery80'
            elif battLevel >= 60:
                battText = 'battery60'
            elif battLevel >= 40:
                battText = 'battery40'
            elif battLevel >= 20:
                battText = 'battery20'
            else:
                battText = 'battery0'

        elif batteryDisplayMode == 2 and battLevel < 20.0:
            battText = 'battery0'
        elif batteryDisplayMode == 2 and battLevel >= 20.0:
            battText = 'batteryHide'

        # Populate the day of week row
        cal_days_of_week = ''
        for i in range(0, 7):
            cal_days_of_week += '<li class="font-weight-bold text-uppercase">' + dayOfWeekText[
                (i + weekStartDay) % 7] + "</li>\n"

        # Populate the date and events
        if maxEventsPerDay == 0:
            if weekCount == 1:
                maxEventsPerDay = 25
            if weekCount == 2:
                maxEventsPerDay = 11
            if weekCount == 3:
                maxEventsPerDay = 8
            if weekCount == 4:
                maxEventsPerDay = 5
            if weekCount == 5:
                maxEventsPerDay = 3
            if weekCount == 6:
                maxEventsPerDay = 2
        cal_events_text = ''
        if weekCount < 3:
            for i in range(len(calList)):
                calList[i] = sorted(calList[i], key=lambda x: x['position'])
        for i in range(len(calList)):
            calGroup = ''
            currDate = calDict['calStartDate'] + timedelta(days=i)
            dayOfMonth = currDate.day
            if currDate == calDict['today']:
                cal_events_text += '<li><div class="datecircle">' + str(dayOfMonth) + '</div>\n'
            elif currDate.month != calDict['referenceDay'].month:
                cal_events_text += '<li><div class="date text-muted">' + str(dayOfMonth) + '</div>\n'
            else:
                cal_events_text += '<li><div class="date">' + str(dayOfMonth) + '</div>\n'
            
            if len(calList[i]) <= maxEventsPerDay:
                maxEvents = maxEventsPerDay
            elif len(calList[i]) > maxEventsPerDay:
                maxEvents = maxEventsPerDay - 1
            for j in range(min(len(calList[i]), maxEvents)):
                event = calList[i][j]
                if weekCount < 3:
                    if event['calendar'] != calGroup:
                        calGroup = event['calendar']
                        cal_events_text += '<div class="group">' + calGroup + '</div>\n'
                cal_events_text += '<div class="event'
                if event['isUpdated']:
                    cal_events_text += ' text-danger'
                elif currDate.month != calDict['referenceDay'].month:
                    cal_events_text += ' text-muted'
                if event['isMultiday']:
                    if event['startDatetime'].date() == currDate:
                        cal_events_text += '">►' + event['summary']
                    elif event['endDatetime'].date() == currDate:
                        cal_events_text += '">◄' + event['summary']
                    else:
                        cal_events_text += '">◄►' + event['summary']
                elif event['allday']:
                    if event['summary'][-14:] == 'hat Geburtstag':
                        cal_events_text += '"><img src="media/cake.png" /> ' + event['summary'][:-15]
                    else:
                        cal_events_text += '">' + event['summary']
                else:
                    cal_events_text += '">' + self.get_short_time(event['startDatetime'], is24hour) + ' ' + event[
                        'summary']
                cal_events_text += '</div>\n'
            if len(calList[i]) > maxEventsPerDay:
                cal_events_text += '<div class="event text-muted">' + str(len(calList[i]) - (maxEvents)) + ' more'

            cal_events_text += '</li>\n'

        # Append the bottom and write the file
        htmlFile = open(self.currPath + '/calendar.html', "w")
        htmlFile.write(calendar_template.format(month=month_name, battText=battText, dayOfWeek=cal_days_of_week, weeks=weekCount,
                                                events=cal_events_text, time=calDict['time']))
        htmlFile.close()

        calBlackImage, calRedImage = self.render_image()

        return calBlackImage, calRedImage
