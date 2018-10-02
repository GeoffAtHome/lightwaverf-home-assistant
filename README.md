# Lightwave RF Component (Platform) for Home Assistant
Here's an integration of LightwaveRF with Home Assistant (HASS).

It's very crude, but does work. It's been working for me for several years with the 1st generation of LightWave kit. I have not tested this with the newer (2nd gen) Lightwave products.

## Caveat
This code may show your devices in the Home Assistant UI, but it may not be able to control the lights for you. The code speaks directly to your Lightwave WiFi Link. Obviously, if you don't have a WiFi Link, then this isn't going to work for you.

Secondly, and most importantly, your device running home assistant (in my case a raspberry pi) needs to be "authorised" to send messages to the WiFi Link. This script does not handle this yet but I plan on implementing this soon.

In the meantime, if you need help with the pairing part, let me know.

If you feel like trying, open a terminal on the device running home assistant and run the following command.

```
echo -ne "100,\!F*p." | nc -u -w1 192.168.1.110 9760
```

This should then show a message on your WiFi Link asking you to pair the device. You have 12 seconds to push the button on the WiFi Link to accept this. Once done, you should be able to control your lights via Home Asssistant.

## Installation
### Adding the Lightwave Component to Home Assistant
The lightwave.py file needs to be placed in the installation directory of Home Assistant. For me this is
```
/custom_components/light/
``` 
There are instructions to follow on the instructions on the home-assistant website. If you need help, let me know.

### Adding LightwaveRF to your configuration file
Now that the component is installed you will need to add the setup to you configuration file.

```
light:
  - platform: lightwave
    host: ip_address of host
    devices:
      R1D1:
        name: Room one Device one
      R1D2:
        name: Room one Device two
      R8D3:
        name: Room eight Device three
   
```
Each **device** requires an **id** and a **name**. The **id** takes the form **R#D#** where **R#** is the room number 
and **D#** is the device number.

If **devices** is missing from your configuration file the component will generate 15 rooms with 8 lights to help you identify the id of each light.

### Acknowledgement
Thanks to Chirag Desai for paving the way to getting this component done.
