# buttons.py
import RPi.GPIO as GPIO
import datetime as dt
from pytz import timezone
from run.run import RunHelper


class ButtonHelper:
    def __init__(self, config):
        self.view_button_pin = config['view_button_pin']
        self.previous_button_pin = config['previous_button_pin']
        self.next_button_pin = config['next_button_pin']
        self.home_button_pin = config['home_button_pin']
        self.displayTZ = config['displayTZ']
        self.defaultView = config['defaultView']

        self.run = RunHelper(config)

        # Set the GPIO mode to BCM
        GPIO.setmode(GPIO.BCM)

        # Set the GPIO pins as inputs with pull-up resistors
        GPIO.setup(self.view_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.previous_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.next_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.home_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Add event detection on button presses
        GPIO.add_event_detect(self.view_button_pin, GPIO.FALLING, callback=self.view_button_callback, bouncetime=200)
        GPIO.add_event_detect(self.previous_button_pin, GPIO.FALLING, callback=self.previous_button_callback, bouncetime=200)
        GPIO.add_event_detect(self.next_button_pin, GPIO.FALLING, callback=self.next_button_callback, bouncetime=200)
        GPIO.add_event_detect(self.home_button_pin, GPIO.FALLING, callback=self.home_button_callback, bouncetime=200)

        # Initialize the current_date and current_view variables
        self.current_date = dt.datetime.now(self.displayTZ).date()
        self.current_view = self.defaultView

    def view_button_callback(self):
        print("View button pressed!")
        # Toggle between "week" and "month" view
        if self.current_view == "week":
            self.current_view = "month"
        else:
            self.current_view = "week"

        # Call maginkcal to update the display with the new view
        self.run.maginkcal(self.current_date, self.current_view, "default")

    def previous_button_callback(self):
        print("Previous button pressed!")
        # Navigate to the previous week/month based on the current view
        if self.current_view == "week":
            self.current_date -= dt.timedelta(days=7)
        else:
            # Assuming each month has 30 days for simplicity, you can modify this part as needed.
            self.current_date -= dt.timedelta(days=30)

        # Call maginkcal to update the display with the new date
        self.run.maginkcal(self.current_date, self.current_view, "default")

    def next_button_callback(self):
        print("Next button pressed!")
        # Navigate to the next week/month based on the current view
        if self.current_view == "week":
            self.current_date += dt.timedelta(days=7)
        else:
            # Assuming each month has 30 days for simplicity, you can modify this part as needed.
            self.current_date += dt.timedelta(days=30)

        # Call maginkcal to update the display with the new date
        self.run.maginkcal(self.current_date, self.current_view, "default")

    def home_button_callback(self):
        print("Home (Refresh) button pressed!")
        # Refresh the calendar display with the current date and default view
        self.run.maginkcal(dt.datetime.now(self.displayTZ).date(), self.defaultView, "default")
