import base64
import json
import os
import paho.mqtt.client as mqtt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# --- CONFIGURACIÓN DEL SERVIDOR ---
# Misma Clave Precompartida (PSK) de 16 bytes configurada en el ESP32
AES_KEY = b"0123456789abcdef" 
BROKER = "127.0.0.1"
PORT = 8883
CA_CERT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mosquitto", "certs", "ca.crt")
USER = "esp32_user"
PASSWORD = "tu_password_segura"
TOPIC = "iot/lab/telemetry"

def decrypt_payload(iv_b64, ciphertext_b64):
    # 1. Decodificar Base64 a bytes crudos
    iv = base64.b64decode(iv_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    
    # 2. Configurar el descifrador AES-128 en modo CBC con el IV recibido
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    
    # 3. Remover el padding PKCS7 y decodificar a texto UTF-8
    padding_len = padded_data[-1]
    plaintext_data = padded_data[:-padding_len]
    
    return plaintext_data.decode('utf-8')

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[SERVIDOR] Conectado exitosamente al broker MQTT.")
        client.subscribe(TOPIC)
        print(f"[SERVIDOR] Escuchando el tópico: {TOPIC}\n")
    else:
        print(f"[SERVIDOR] Error de conexión, código: {rc}")

def on_message(client, userdata, msg):
    try:
        # Recibir el JSON estructurado por el ESP32
        payload_raw = json.loads(msg.payload.decode('utf-8'))
        iv_b64 = payload_raw["iv"]
        data_b64 = payload_raw["data"]
        
        print(f"[RECIBIDO MQTT] IV (B64): {iv_b64}")
        print(f"[RECIBIDO MQTT] Data Cifrada (B64): {data_b64}")
        
        # Descifrar el payload
        decrypted_json = decrypt_payload(iv_b64, data_b64)
        print(f"👉 [JSON DESCIFRADO EXITOSAMENTE] -> {decrypted_json}\n")
        
    except Exception as e:
        print(f"[ERROR] No se pudo descifrar el mensaje: {e}\n")

# Inicializar cliente MQTT del servidor (Compatible con paho-mqtt v2.x)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.tls_set(ca_certs=CA_CERT)
client.username_pw_set(USER, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

# Conectar al broker local de Docker
client.connect(BROKER, PORT, 60)

# Mantener el servidor activo escuchando
client.loop_forever()