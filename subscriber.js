const mqtt = require('mqtt');
const crypto = require('crypto');

// --- CONFIGURACIÓN DEL BROKER Y SEGURIDAD ---
const MQTT_BROKER = 'mqtt://localhost:1883';
const MQTT_TOPIC = 'iot/lab/telemetry';
const MQTT_OPTIONS = {
    username: 'esp32_user',
    password: 'tu_password_segura'
};

// Debe ser exactamente la misma clave de 16 bytes que usaste en el ESP32
const AES_KEY = Buffer.from('0123456789abcdef', 'utf8');

// Conectar al broker MQTT local (Docker)
const client = mqtt.connect(MQTT_BROKER, MQTT_OPTIONS);

client.on('connect', () => {
    console.log('[CONECTADO] Escuchando mensajes en el broker MQTT...');
    client.subscribe(MQTT_TOPIC, (err) => {
        if (!err) {
            console.log(`[SUSCRITO] Tópico activo: ${MQTT_TOPIC}`);
        }
    });
});

client.on('message', (topic, message) => {
    try {
        console.log('\n----------------------------------------');
        console.log('[MENSAJE CRUDO RECIBIDO]:', message.toString());

        // 1. Parsear el JSON recibido {"iv": "...", "data": "..."}
        const payload = JSON.parse(message.toString());
        
        if (!payload.iv || !payload.data) {
            console.error('[ERROR] El mensaje no tiene el formato esperado (iv/data).');
            return;
        }

        // 2. Decodificar Base64 a Buffers
        const ivBuffer = Buffer.from(payload.iv, 'base64');
        const ciphertextBuffer = Buffer.from(payload.data, 'base64');

        // 3. Descifrar usando AES-128-CBC
        // Nota: Node.js maneja automáticamente el PKCS7 padding por defecto al especificar el algoritmo
        const decipher = crypto.createDecipheriv('aes-128-cbc', AES_KEY, ivBuffer);
        
        let decrypted = decipher.update(ciphertextBuffer);
        decrypted = Buffer.concat([decrypted, decipher.final()]);

        // 4. Convertir el resultado descifrado a texto (JSON original) y parsearlo
        const decryptedString = decrypted.toString('utf8');
        const sensorData = JSON.parse(decryptedString);

        console.log('[DESCIFRADO EXITOSO E2E] Datos recuperados:');
        console.table(sensorData);

        // Validación opcional de frescura (Anti-Replay con timestamp)
        const currentTimestamp = Date.now();
        const packetAge = currentTimestamp - sensorData.timestamp;
        console.log(`[SEGURIDAD] Antigüedad del paquete: ~${packetAge} ms`);

    } catch (error) {
        console.error('[ERROR DE DESCIFRADO]:', error.message);
    }
});
