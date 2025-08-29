# Fermax Meet Me Integration in Homeassistant throws mqtt 

# Introduction

I create a server that simulate fermax management software use IP and port to receive information of Fermax Meet Me Milo 1L when button it is pressed, save image, and send MQTT motion on event

Fermax Meet Me Milo 1L --> Docker Fermax server Integration --> Mqtt --> Homeassistant

# Instalation

You need to create docker image, downlad repository and launch

```
docker build -t fermaxserver -f Dockerfile .
```

Run this image with

```
docker run --name fermaxserver -tid \
  --restart unless-stopped \
  -p "9800:9800" \
  -v /home/docker/fermaxserver/config:/app/config \
  -v /etc/localtime:/etc/localtime:ro \
  -v /etc/timezone:/etc/timezone:ro \
  fermaxserver:latest
```

Change config.json with correct MQTT server info

```
    {
      "MQTTserver": "192.168.x.x",
      "MQTTuser": "user",
      "MQTTpass": "pass"
    }
```

Create new binary_sensor in Homeassistant:

```
mqtt:
  binary_sensor:
    - name: motion_milo
      device_class: motion
      state_topic: "home-assistant/192.168.x.x/motion"
      payload_on: "ON"
      payload_off: "OFF"
```
