"""
homeassistant.components.light.lightwave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Implements LightwaveRF lights.


My understanding of the LightWave Hub is that devices cannot be discovered so must be
registered manually. This is done in the configuration file:

switch:
  - platform: lightwave
    host: ip_address
    devices:
      R1D2:
        name: Room one Device two
      R2D1:
        name: Room two Device one

Each device requires an id and a name. THe id takes the from R#D# where R# is the room number 
and D# is the device number.

If devices are missing the default is to generate 15 rooms with 8 lights. From this you will
be able to determine the room and device number for each light.

TODO: 
Add a registration button. Until then the following command needs to be sent to the LightwaveRF hub:
    echo -ne "100,\!F*p." | nc -u -w1 LW_HUB_IP_ADDRESS 9760

When this is sent you have 12 seconds to acknowledge the message on the hub.

For more details on the api see: https://api.lightwaverf.com/
"""

import asyncio
import queue
import threading
import socket
import time
import logging
import voluptuous as vol
from homeassistant.const import CONF_DEVICES, CONF_NAME, CONF_HOST
from homeassistant.components.light import (
    Light, ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA}
})

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Find and return LightWave lights """
    _LOGGER.info("LW Light started!")
    lights = []
    host = config.get(CONF_HOST)
    _LOGGER.info("LW Host: " + host)
    lwlink = LWLink(host)

    for device_id, device_config in config.get(CONF_DEVICES, {}).items():
        name = device_config[CONF_NAME]
        lights.append(LRFLight(name, device_id, lwlink))

    if len(lights) == 0:
        # Config is empty so generate a default set of switches
        for room in range(1, 15):
            for device in range(1, 8):
                name = "Room " + str(room) + " Device " + str(device)
                device_id = "R" + str(room) + "D" + str(device)
                lights.append(LRFLight(name, device_id, lwlink))

    async_add_entities(lights)
    _LOGGER.info("LW Light complete!")


class LWLink():
    SOCKET_TIMEOUT = 2.0
    RX_PORT = 9761
    TX_PORT = 9760

    the_queue = queue.Queue()
    thread = None
    link_ip = ''

    # msg = "100,!F*p."

    def __init__(self, link_ip=None):
        if link_ip != None:
            LWLink.link_ip = link_ip

    # methods
    def send_message(self, msg):
        LWLink.the_queue.put_nowait(msg)
        if LWLink.thread == None or not self.thread.isAlive():
            LWLink.thread = threading.Thread(target=self._startSending)
            LWLink.thread.start()

    def _startSending(self):
        while not LWLink.the_queue.empty():
            self._send_reliable_message(LWLink.the_queue.get_nowait())

    def _send_reliable_message(self, msg):
        """ Send msg to LightwaveRF hub and only returns after:
             an OK is received | timeout | exception | max_retries """
        result = False
        max_retries = 15
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as write_sock:
                write_sock.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as read_sock:
                    read_sock.setsockopt(
                        socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    read_sock.settimeout(LWLink.SOCKET_TIMEOUT)
                    read_sock.bind(('0.0.0.0', LWLink.RX_PORT))
                    while max_retries:
                        max_retries -= 1
                        write_sock.sendto(msg.encode(
                            'UTF-8'), (LWLink.link_ip, LWLink.TX_PORT))
                        result = False
                        while True:
                            response, dummy = read_sock.recvfrom(1024)
                            response = response.decode('UTF-8').split(',')[1]
                            if response.startswith('OK'):
                                result = True
                                break
                            if response.startswith('ERR'):
                                break

                        if result:
                            break

                        time.sleep(0.25)

        except socket.timeout:
            return result

        return result


def calculate_brightness(brightness):
    """Scale brightness from 0..255 to 0..32"""
    return round((brightness * 32) / 255)


class LRFLight(Light):
    """ Provides a LightWave light. """

    def __init__(self, name, device_id, lwlink):
        self._name = name
        self._device_id = device_id
        self._state = None
        self._brightness = 255
        self._lwlink = lwlink

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

    async def async_turn_on(self, **kwargs):
        """ Turn the LightWave light on. """
        self._state = True
        msg = ''

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            brightness_value = calculate_brightness(self._brightness)
            # F1 = Light on and F0 = light off. FdP[0..32] is brightness. 32 is
            # full. We want that when turning the light on.
            msg = '321,!%sFdP%d|Lights %d|%s' % (
                self._device_id, brightness_value, brightness_value, self._name)
        else:
            msg = '321,!%sFdP32|Turn On|%s' % (self._device_id, self._name)

        self._lwlink.send_message(msg)
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the LightWave light off. """
        self._state = False

        msg = "321,!%sF0|Turn Off|%s" % (self._device_id, self._name)
        self._lwlink.send_message(msg)

        self.async_schedule_update_ha_state()
