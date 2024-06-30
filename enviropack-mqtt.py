# enviropack-mqtt.py
#
# An all-singing, all-dancing script for the Pico Enviro+ Pack; it reads all
# sensors, displays them nicely *and* sends them to MQTT. It draws heavily on
# the examples, but with some display and useability changes.
#
# Copyright(C) 2024 Pete Favelle <rp2040@ahnlak.com>
#
# This file is distributed under the MIT License - see LICENSE for details.


#################
# Configuration #
#################

# These values define our behaviour; this is the only section you should
# need to edit

# Wireless settings (UK country code is 'GB')
WIFI_SSID         = "YOUR_WIFI_SSID"          # WiFi SSID
WIFI_PASS         = "YOUR_WIFI_PASSWORD"      # WiFi Password
WIFI_CC           = "YOUR_COUNTRY_CODE"       # ISO 3166-1 country code

# MQTT settings
MQTT_CLIENT_ID    = "EnviroPlusPack"          # The client ID
MQTT_BROKER_IP    = "YOUR_BROKER_IP"          # IP of your MQTT broker server
MQTT_BROKER_USER  = "YOUR_BROKER_USERNAME"    # Username for your broker
MQTT_BROKER_PASS  = "YOUR_BROKER_PASSWORD"    # Password for your broker
MQTT_UPDATE_FREQ  = 60                        # Seconds between MQTT updates

# Corrections, to try and normalise the readings
CORRECT_TEMP      = -7.5                      # Seems to be the USB-powered bump
CORRECT_ALTITUDE  = 75                        # Altitude in metres


###################
# Library imports #
###################

# Import everything we'll need; this is all rolled into the Pimoroni uf2
import time
import uasyncio
from   machine          import Pin, ADC
from   picographics     import PicoGraphics, DISPLAY_ENVIRO_PLUS
from   pimoroni         import RGBLED, Button
from   breakout_bme68x  import BreakoutBME68X, STATUS_HEATER_STABLE
from   pimoroni_i2c     import PimoroniI2C
from   breakout_ltr559  import BreakoutLTR559

# The next imports require local files from this repo
from   network_manager  import NetworkManager

# And these imports need to be added via Thonny's "Manage Packages"
# (or add them manually to /lib)
import umqtt.simple


#############
# Functions #
#############


def read_bme():
  """
  Reads the values we know about from the BME688 sensor; the processed
  values are then stored in our global variables:

  final_temperature, final_pressure, final_humidity

  We don't bother with gas figures, because ... they're not very useful.
  """
  global final_temperature, final_pressure, final_humidity

  # Fetch what we can from the sensor, check the status of the read
  temperature, pressure, humidity, _, status, _, _ = bme.read(heater_temp=0, heater_duration=0)

  # Only process if the 'new data' flag is set
  if not status & 0x80:
    return

  # Process the temperature reading - essentially we just add a correction
  final_temperature = temperature + CORRECT_TEMP

  # Process the pressure reading; need to apply an altitude correction
  # (this correction is from the Pimoroni examples - I don't understand it!)
  final_pressure = (pressure / 100) + \
                   (((pressure / 100) * 9.80665 * CORRECT_ALTITUDE) / \
                    (287 * final_temperature + (CORRECT_ALTITUDE / 400)))

  # Process the humidity reading; correct for temperature / dewpoint
  dewpoint = temperature - ((100 - humidity) / 5)
  final_humidity = 100 - (5 * (final_temperature - dewpoint))



def render_display():
  """
  Draws the current state on the screen; this will generally involve the
  various sensor readings, along with any required diagnostics
  """

  # Set the led to indicate how things are going...
  led.set_rgb(0, 0, 0)

  # Clear the display
  display.set_pen(BLACK)
  display.clear()

  # draw the top box, with time / date showing
  for x in range(0,16):
        for y in range(8,12):
            display.sprite(x, y, x*8, (y-8)*8)
            display.sprite(x, y+4, (x+16)*8, (y-8)*8)
  display.set_pen(WHITE)
  year, month, day, hour, minute, second, weekday, yearday = time.localtime()

  display.text(f"{hour:02n}", 5, 5, scale=3)
  display.text(":", 36, 5, scale=3)
  display.text(f"{minute:02n}", 42, 5, scale=3)
  display.text(":", 73, 5, scale=3)
  display.text(f"{second:02n}", 79, 5, scale=3)
  
  display.text(f"{day:02n}", 119, 5, scale=3)
  display.text("/", 153, 5, scale=3)
  display.text(f"{month:02n}", 167, 5, scale=3)
  display.text("/", 196, 5, scale=3)
  display.text(f"{year-2000:02n}", 210, 5, scale=3)

  # pick a pen colour based on the temperature
  display.set_pen(GREEN)
  if final_temperature > 30:
      display.set_pen(RED)
  if final_temperature < 10:
      display.set_pen(CYAN)
  display.text(f"{final_temperature:.1f}°C", (WIDTH - display.measure_text(f"{final_temperature:.1f}°C", scale=4)) // 2, 75, WIDTH, scale=4)

  # Divide the lower part of the screen (two lines ~= 64 pixels)
  display.set_pen(YELLOW)
  display.line(123, 170, 123, 240)
  display.line(0, 170, 240, 170)

  # Top left for temperature
  for x in range(12,16):
        for y in range(0,4):
            display.sprite(x, y, (x - 12) * 8, (y + 22) * 8)
  display.set_pen(WHITE)
  display.text(f"{final_temperature:02.1f}", 30, 178, scale=3)
  display.text("°C", 85, 185, scale=2)

  # Top right for humidity
  for x in range(0,4):
        for y in range(0,4):
            display.sprite(x, y, (x + 16) * 8, (y + 22) * 8)
  display.set_pen(WHITE)
  display.text(f"{final_humidity:02.1f}", 160, 178, scale=3)
  display.text("%", 215, 185, scale=2)

  # Bottom left is pressure
  for x in range(4,8):
        for y in range(0,4):
            display.sprite(x, y, (x - 4) * 8, (y + 26) * 8)
  display.set_pen(WHITE)
  display.text(f"{final_pressure:4.0f}", 90 - display.measure_text(f"{final_pressure:4.0f}", scale=3), 210, scale=3)
  display.text("hPa", 90, 215, scale=2)

  # And bottom right is lux
  for x in range(8,12):
        for y in range(0,4):
            display.sprite(x, y, (x + 8) * 8, (y + 26) * 8)
  display.set_pen(WHITE)
  display.text(f"{final_lux:3.0f}", 205 - display.measure_text(f"{final_lux:3.0f}", scale=3), 210, scale=3)
  display.text("lux", 205, 215, scale=2)

  # Finally, update the display
  display.update()    


###################
# Main Entrypoint #
###################

# Set up the display, LED and buttons
display = PicoGraphics(display=DISPLAY_ENVIRO_PLUS)
display.set_font("bitmap8")
display.load_spritesheet("enviropack-mqtt.rgb332")
led = RGBLED(6, 7, 10, invert=True)
button_a = Button(12, invert=True)
button_b = Button(13, invert=True)
button_x = Button(14, invert=True)
button_y = Button(15, invert=True)

# Set up I2C, which we use to talk to the sensors
i2c = PimoroniI2C(4, 5)
bme = BreakoutBME68X(i2c, address=0x77)
ltr = BreakoutLTR559(i2c)

# Create some pseudo-constants
WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)
RED = display.create_pen(255, 0, 0)
GREEN = display.create_pen(0, 255, 0)
CYAN = display.create_pen(0, 255, 255)
MAGENTA = display.create_pen(200, 0, 200)
YELLOW = display.create_pen(200, 200, 0)
BLUE = display.create_pen(0, 0, 200)
GREY = display.create_pen(75, 75, 75)
WIDTH, HEIGHT = display.get_bounds()

# Initialise our various readings
final_temperature = 0
final_pressure = 0
final_humidity = 0
final_lux = 0

# Now enter the main processing loop
while True:

  # Check the button states

  # Fetch readings from our various sensors
  read_bme()

  # Render the display
  render_display()

  # Check to see if an MQTT update is due

  # Wait briefly before the next cycle
  time.sleep(1)