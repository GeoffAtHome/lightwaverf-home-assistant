"""
homeassistant.components.light.lightwave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Implements LightwaveRF lights.


My understanding of the LightWave Hub is that devices cannot be discovered so must be
registered manually. This is done in the configuration file:

light:
  - platform: lightwave
    devices:
      R1D2:
        name: Room one Device two
      R2D1:
        name: Room two Device one

Each device requires an id and a name. The id takes the form R#D# where R# is the room number 
and D# is the device number.

If devices are missing the default is to generate 15 rooms with 8 lights. From this you will
be able to determine the room and device number for each light.

TODO: 
Add a registration button. Until then the following command needs to be sent to the LightwaveRF hub:
    echo -ne "100,\!F*p." | nc -u -w1 LW_HUB_IP_ADDRESS 9760

When this is sent you have 12 seconds to acknowledge the message on the hub.

For more details on the api see: https://api.lightwaverf.com/
"""

import socket
import voluptuous as vol

from homeassistant.const import CONF_DEVICES, CONF_NAME
from homeassistant.components.light import (
    Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA}
})


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """ Find and return LightWave lights """
    lights = []

    for device_id, device_config in config.get(CONF_DEVICES, {}).items():
        name = device_config[CONF_NAME]
        lights.append(LRFLight(name, device_id))

    if len(lights) == 0:
        # Config is empty so generate a default set of switches
        for room in range(1, 15):
            for device in range(1, 8):
                name = "Room " + str(room) + " Device " + str(device)
                device_id = "R" + str(room) + "D" + str(device)
                lights.append(LRFLight(name, device_id))

    add_devices_callback(lights)


def send_command(msg):
    """ send message to LightwaveRF hub."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(msg.encode('UTF-8'), ('255.255.255.255', 9760))
    sock.close


def calculate_brightness(brightness):
    """Scale brightness from 0..255 to 0..32"""
    return round((brightness * 32) / 255)


class LRFLight(Light):
    """ Provides a LightWave light. """

    def __init__(self, name, device_id):
        self._name = name
        self._device_id = device_id
        self._state = None
        self._brightness = 255

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def should_poll(self):
        """ No polling needed for a LightWave light. """
        return False

    @property
    def name(self):
        """ Returns the name of the LightWave light. """
        return self._name

    @property
    def brightness(self):
        """ Brightness of this light between 0..255. """
        return self._brightness

    @property
    def is_on(self):
        """ True if the LightWave light is on. """
        return self._state

    def turn_on(self, **kwargs):
        """ Turn the LightWave light on. """
        self._state = True

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            brightness_value = calculate_brightness(self._brightness)
            msg = '321, !%sFdP%d|Lights %d|%s ' % (
                self._device_id, brightness_value, brightness_value, self._name)
            send_command(msg)

        # F1 = Light on and F0 = light off. FdP[0..32] is brightness. 32 is
        # full. We want that when turning the light on.
        msg = '321, !%sFdP32|Turn On|%s ' % (self._device_id, self._name)
        send_command(msg)

        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """ Turn the LightWave light off. """
        self._state = False

        msg = "321, !%sF0|Turn Off|%s " % (self._device_id, self._name)
        send_command(msg)
        self.schedule_update_ha_state()
