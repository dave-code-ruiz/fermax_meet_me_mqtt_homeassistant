import socket
import json
import struct
import time
import logging
import os
import paho.mqtt.client as mqtt
from base64 import b64encode

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s fermax-meet-server[] %(message)s')

def build_packet(packet_type, params):
    pkt_prefix_1 = [0xff, 0x00, 0x00, 0x00]
    pkt_prefix_2 = [0x00, 0x00, 0x00, 0x00]
    pkt_type = []

    if packet_type == 'login':
        pkt_type = [0x00, 0x00, 0xe8, 0x03]
    elif packet_type == 'info':
        pkt_type = [0x00, 0x00, 0xfc, 0x03]

    sid = int(params['SessionID'], 16)

    pkt_prefix_data = struct.pack('4B', *pkt_prefix_1) + struct.pack('i', sid) + struct.pack('4B', *pkt_prefix_2) + struct.pack('4B', *pkt_type)
    pkt_params_data = json.dumps(params).encode('utf-8')
    pkt_data = pkt_prefix_data + struct.pack('i', len(pkt_params_data)) + pkt_params_data

    return pkt_data

def get_config(key):
    filename = 'config/config.json'
    with open(filename, 'r', encoding='utf-8') as f:
        config = json.load(f)
    for item in config:
        if key in item:
            return item[key]
    return None

def get_reply_head(sock):
    reply_head = {}
    for i in range(4):
        data = sock.recv(4)
        if len(data) != 4:
            raise ValueError(f"Expected 4 bytes, but received {len(data)} bytes")
        reply_head[f'Prefix{i + 1}'] = struct.unpack('<I', data)[0]  # Use unsigned 32-bit integer
    reply_head['Content_Length'] = reply_head.pop('Prefix4')
    
    # Validate Content_Length to ensure it's within a reasonable range
    # if not (0 <= reply_head['Content_Length'] <= 10**7):  # Example range
    #    raise ValueError(f"Invalid Content_Length: {reply_head['Content_Length']}")
    
    return reply_head

def mqtt_publish(topic, message):
    mqtt_server = get_config("MQTTserver")
    mqtt_user = get_config("MQTTuser")
    mqtt_pass = get_config("MQTTpass")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(mqtt_user, mqtt_pass)
    client.connect(mqtt_server)
    client.publish(topic, message, retain=True)
    client.disconnect()

    logging.info(f"Mqtt user {mqtt_user} message sent {topic} => {message}")

def send_image_via_mqtt(image_path, host):
    
    url = obtener_url(image_path)

    mqtt_publish(f"home-assistant/{host}/imagen", url)

    logging.info(f"Image sent via MQTT to topic home-assistant/{host}/imagen from path '{image_path}'")

def obtener_url(image_path):
    #TODO crear un volumen para las imagenes, guardarla en dicho volumen y devolver la url
    with open(image_path, "rb") as image_file:
        encoded_string = b64encode(image_file.read()).decode('utf-8')
    url = f"data:image/jpeg;base64,{encoded_string}"
    return url

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 9800))
    server_socket.listen(1)
    logging.info("Socket created on port 9800")
    mqtt_publish("test", "ON")
    try:
        while True:
            try:
                client_socket, client_address = server_socket.accept()
                logging.info(f"Connected from {client_address[0]}")
                client_socket.settimeout(10)
                pid = os.fork()
                if pid == 0:  # Child process
                    logging.info("Child process started.")
                    reply = get_reply_head(client_socket)
                    data = client_socket.recv(reply['Content_Length'])
                    bytes_received = len(data)
                    logging.info(f"bytes_received: {bytes_received} content_length: {reply['Content_Length']}")

                    """ if bytes_received < reply['Content_Length']:
                        logging.info("Receiving adicional data...")
                        buffer = data
                        reply = get_reply_head(client_socket)
                        data = client_socket.recv(reply['Content_Length'])
                        buffer += data
                        bytes_received += len(data)
                        data = buffer
                        logging.info(f"adicional data bytes_received: {bytes_received} content_length: {reply['Content_Length']}") """

                    # Extract leading numeric characters if present
                    leading_chars = b''
                    while data[:1].isdigit():
                        leading_chars += data[:1]
                        data = data[1:]  # Remove the digit from data

                    # Skip spaces or non-printable characters after the numeric data
                    while data[:1] in b' \x00':
                        data = data[1:]

                    if leading_chars:
                        logging.info(f"Datos de la placa (binarios): {leading_chars}")

                    # Check if data starts with JPEG header
                    if data.startswith(b'\xFF\xD8\xFF'):
                        logging.info("JPEG file detected.")
                        if b'\xFF\xD9' in data:
                            data, discarded_data = data.split(b'\xFF\xD9', 1)
                            data += b'\xFF\xD9'
                            logging.info(f"Discarded data after FF D9: '{discarded_data}'")
                        else:
                            data += b'\xFF\xD9'
                            logging.warning("No FF D9 marker found. Added manually.")

                        timestamp = int(time.time())
                        filename = f"config/{timestamp}.jpg"
                        with open(filename, 'wb') as f:
                            f.write(data)
                        logging.info(f"JPEG file saved successfully at {filename}.")
                        
                        # send_image_via_mqtt(filename, client_address[0])

                    mqtt_publish(f"home-assistant/{client_address[0]}/motion", "ON")
                    time.sleep(5)
                    mqtt_publish(f"home-assistant/{client_address[0]}/motion", "OFF")

            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(1)
    finally:
        client_socket.close()
        logging.info("Client socket closed.")
        # Close the server socket
        server_socket.close()
        logging.info("Server socket closed.")
        os._exit(0)

if __name__ == "__main__":
    main()