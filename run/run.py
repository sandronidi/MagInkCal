import datetime as dt

from pytz import timezone
from gcal.gcal import GcalHelper
from render.render import RenderHelper
from power.power import PowerHelper
import logging

class RunHelper:

    def __init__(self, config):
        self.logger = logging.getLogger('maginkcal')

        self.piSugar2Present = config['piSugar2Present']
        self.weekStartToday = config['weekStartToday']
        self.monthStartToday = config['monthStartToday']
        self.weekStartDay = config['weekStartDay']
        self.displayTZ = timezone(config['displayTZ'])
        self.thresholdHours = config['thresholdHours']
        self.batteryDisplayMode = config['batteryDisplayMode']
        self.calendars = config['calendars']
        self.dayOfWeekText = config['dayOfWeekText']
        self.maxEventsPerDay = config['maxEventsPerDay']
        self.is24hour = config['is24h']
        self.screenHeight = config['screenHeight']
        self.screenWidth = config['screenWidth']
        self.imageWidth = config['imageWidth']
        self.imageHeight = config['imageHeight']
        self.rotateAngle = config['rotateAngle']
        self.isDisplayToScreen = config['isDisplayToScreen']
        self.isShutdownOnComplete = config['isShutdownOnComplete']


    def setCalStartEndTime(self,date, range, startToday, weekStartDay):
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


    def maginkcal(self, date, view, startToday):
        self.logger.info("Starting calendar update")

        try:
            # Establish current date and time information
            # Note: For Python datetime.weekday() - Monday = 0, Sunday = 6
            # For this implementation, each week starts on a Sunday and the calendar begins on the nearest elapsed Sunday
            # The calendar will also display 5 weeks of events to cover the upcoming month, ending on a Saturday
            if self.piSugar2Present:
                powerService = PowerHelper()
                powerService.sync_time()
                currBatteryLevel = powerService.get_battery()
                self.logger.info('Battery level at start: {:.3f}'.format(currBatteryLevel))
            else:
                self.logger.info('no piSugar2 present set Dummy values')
                currBatteryLevel = 100

            if startToday == "default":
                if view == "week":
                    startToday = self.weekStartToday
                elif view == "month":
                    startToday = self.monthStartToday
                    
            currDatetime = dt.datetime.now(self.displayTZ)
            self.logger.info("Time synchronised to {}".format(currDatetime))
            currDate = currDatetime.date()
            calRange = self.setCalStartEndTime(date, view, startToday, self.weekStartDay)
            calStartDatetime = self.displayTZ.localize(dt.datetime.combine(calRange['StartDate'], dt.datetime.min.time()))
            calEndDatetime = self.displayTZ.localize(dt.datetime.combine(calRange['EndDate'], dt.datetime.max.time()))

            # Using Google Calendar to retrieve all events within start and end date (inclusive)
            start = dt.datetime.now()
            gcalService = GcalHelper()
            eventList = gcalService.retrieve_events(self.calendars, calStartDatetime, calEndDatetime, self.displayTZ, self.thresholdHours)
            #eventList = []
            self.logger.info("Calendar events retrieved in " + str(dt.datetime.now() - start))

            # Populate dictionary with information to be rendered on e-ink display
            calDict = {'events': eventList, 'calStartDate': calRange['StartDate'], 'today': currDate, 'lastRefresh': currDatetime,
                    'batteryLevel': currBatteryLevel, 'batteryDisplayMode': self.batteryDisplayMode,
                    'dayOfWeekText': self.dayOfWeekText, 'weekStartDay': self.weekStartDay, 'maxEventsPerDay': self.maxEventsPerDay,
                    'is24hour': self.is24hour, 'calRange': calRange['Range'], 'referenceDay': date}

            renderService = RenderHelper(self.imageWidth, self.imageHeight, self.rotateAngle)
            calBlackImage, calRedImage = renderService.process_inputs(calDict)

            if self.isDisplayToScreen:
                from display.display import DisplayHelper
                displayService = DisplayHelper(self.screenWidth, self.screenHeight)
                if currDate.weekday() == self.weekStartDay:
                    # calibrate display once a week to prevent ghosting
                    displayService.calibrate(cycles=0)  # to calibrate in production
                displayService.update(calBlackImage, calRedImage)
                displayService.sleep()
            if self.piSugar2Present:
                currBatteryLevel = powerService.get_battery()
                self.logger.info('Battery level at end: {:.3f}'.format(currBatteryLevel))

        except Exception as e:
            self.logger.error(e)

        self.logger.info("Completed calendar update")

        self.logger.info("Checking if configured to shutdown safely - Current hour: {}".format(currDatetime.hour))
        if self.isShutdownOnComplete:
            # implementing a failsafe so that we don't shutdown when debugging
            # checking if it's 6am in the morning, which is the time I've set PiSugar to wake and refresh the calendar
            # if it is 6am, shutdown the RPi. if not 6am, assume I'm debugging the code, so do not shutdown
            if currDatetime.hour == 6:
                self.logger.info("Shutting down safely.")
                import os
                os.system("sudo shutdown -h now")