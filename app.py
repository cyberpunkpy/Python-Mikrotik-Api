from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import sqlite3
import requests
import routeros_api

load_dotenv()

app = Flask(__name__)

# Configuración del bot de Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
MIKROTIK_HOST = os.getenv("MIKROTIK_HOST")
MIKROTIK_USERNAME = os.getenv("MIKROTIK_USERNAME")
MIKROTIK_PASSWORD = os.getenv("MIKROTIK_PASSWORD")

#procesamiento de address list de mkt antes que nada.

def get_mikrotik_addresses():
    """
    Obtiene las IPs de la address-list de MikroTik.
    """
    try:
        connection = routeros_api.RouterOsApiPool(
            MIKROTIK_HOST,
            username=MIKROTIK_USERNAME,
            password=MIKROTIK_PASSWORD,
            port=8728,
            plaintext_login=True
        )
        api = connection.get_api()

        # Obtener el address list
        address_list = api.get_resource('/ip/firewall/address-list')
        items = address_list.get()

        # Desconectar
        connection.disconnect()

        # Retornar las direcciones en formato simple
        return [item['address'] for item in items]

    except routeros_api.exceptions.RouterOsApiConnectionError as e:
        print(f"Error de conexión: {e}")
        return []
    except Exception as e:
        print(f"Error inesperado: {e}")
        return []

#sincronizamos datos de mkt ip de address list con ip de bd

def sync_with_mikrotik():
    """
    Sincroniza la base de datos con las IPs actuales en MikroTik.
    """
    mikrotik_addresses = get_mikrotik_addresses()

    # Abre la conexión a la base de datos
    with sqlite3.connect("access_requests.db") as conn:
        cursor = conn.cursor()

        # Obtén todas las IPs aprobadas en la base de datos
        cursor.execute("SELECT ip FROM requests WHERE status = 'aprobado'")
        db_addresses = [row[0] for row in cursor.fetchall()]

        # Compara con las IPs en MikroTik
        for ip in db_addresses:
            if ip not in mikrotik_addresses:
                # Cambia el estado a "eliminada"
                cursor.execute("UPDATE requests SET status = 'eliminada' WHERE ip = ?", (ip,))
        
        conn.commit()



#telegram procesamiento msj

@app.route(f"/telegram/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    """
    Recibe mensajes desde Telegram y maneja los comandos.
    """
    update = request.json
    print(update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        if text.startswith("/approve"):
            return handle_approve(chat_id, text)

        elif text.startswith("/reject"):
            return handle_reject(chat_id, text)

        else:
            return send_message(chat_id, "Comando no reconocido. Usa /approve <ID> o /reject <ID>.")

    return jsonify({"status": "ignored"}), 200

# Ruta para la página principal (índice)
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/request_access", methods=["GET", "POST"])
def request_access():
    """
    Permite que un técnico registre una solicitud de acceso.
    """
    if request.method == "POST":
        ip = request.form.get("ip")
        comment = request.form.get("comment", "")

        if not ip:
            return "IP es requerida", 400

        # Insertar solicitud en la base de datos
        with sqlite3.connect("access_requests.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO requests (ip, comment, status) VALUES (?, ?, 'pendiente')",
                (ip, comment),
            )
            conn.commit()

            # Obtener el ID de la solicitud recién creada
            request_id = cursor.lastrowid

        # Notificar al administrador (opcional)
        notify_admin(ip, comment, request_id)

        return "Solicitud registrada correctamente. Espera la aprobación.", 200

    return render_template("request_access.html")

@app.route("/check_status", methods=["POST"])
def check_status():
    ip = request.form.get("ip")
    if not ip:
        return """
        <p>La dirección IP es requerida.</p>
        <a href="/" style="text-decoration:none;color:blue;">Volver a Inicio</a>
        """, 400

    #sincroniza con funcion api mkt arriba
    sync_with_mikrotik()

    # Consulta el estado de la IP en la base de datos
    with sqlite3.connect("access_requests.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM requests WHERE ip = ?", (ip,))
        result = cursor.fetchone()

    if result:
        return f"""
        <p>Estado de la IP {ip}: {result[0]}</p>
        <a href="/" style="text-decoration:none;color:blue;">Volver a Inicio</a>
        """
    else:
        return f"""
        <p>No se encontró ninguna solicitud para la IP {ip}.</p>
        <a href="/" style="text-decoration:none;color:blue;">Volver a Inicio</a>
        """


def handle_approve(chat_id, text):
    """
    Maneja el comando /approve para aprobar solicitudes.
    """
    try:
        request_id = int(text.split()[1])
    except (IndexError, ValueError):
        return send_message(chat_id, "Formato incorrecto. Usa /approve <ID>.")

    with sqlite3.connect("access_requests.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ip, comment FROM requests WHERE id = ? AND status = 'pendiente'", (request_id,))
        row = cursor.fetchone()

        if not row:
            return send_message(chat_id, "Solicitud no encontrada o ya procesada.")
        
        ip, comment = row

        # Agregar IP al MikroTik
        response = add_ip_to_mikrotik(ip, comment=comment)
        if response.get("status") == "success":
            cursor.execute("UPDATE requests SET status = 'aprobado' WHERE id = ?", (request_id,))
            conn.commit()
            return send_message(chat_id, f"IP {ip} aprobada y agregada al MikroTik.")
        else:
            return send_message(chat_id, f"Error al agregar la IP {ip} al MikroTik: {response.get('error')}")


def handle_reject(chat_id, text):
    """
    Maneja el comando /reject para rechazar solicitudes.
    """
    try:
        request_id = int(text.split()[1])
    except (IndexError, ValueError):
        return send_message(chat_id, "Formato incorrecto. Usa /reject <ID>.")

    with sqlite3.connect("access_requests.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ip FROM requests WHERE id = ? AND status = 'pendiente'", (request_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE requests SET status = 'rechazado' WHERE id = ?", (request_id,))
            conn.commit()
            return send_message(chat_id, f"Solicitud {request_id} rechazada.")
        else:
            return send_message(chat_id, "Solicitud no encontrada o ya procesada.")


def notify_admin(ip, comment, request_id):
    """
    Notifica al administrador sobre una nueva solicitud de acceso.
    """
    message = f"🔔 Nueva solicitud de acceso:\nIP: {ip}\nComentario: {comment}\nID de solicitud: {request_id}\n\nUsa /approve {request_id} para aprobar o /reject {request_id} para rechazar."
    send_message(ADMIN_CHAT_ID, message)


def add_ip_to_mikrotik(ip, list_name="acc_ext_ok", comment="Acceso por medio de Python API-->"):
    """
    Agrega una dirección IP al address list en MikroTik.
    """
    try:
        # Conexión al MikroTik
        connection = routeros_api.RouterOsApiPool(
            MIKROTIK_HOST,
            username=MIKROTIK_USERNAME,
            password=MIKROTIK_PASSWORD,
            port=8728,
            plaintext_login=True
        )
        api = connection.get_api()

        # Agregar la dirección IP al address list
        address_list = api.get_resource('/ip/firewall/address-list')
        address_list.add(
            address=ip,
            list=list_name,
            comment=comment
        )
        connection.disconnect()
        return {"status": "success"}
    except routeros_api.exceptions.RouterOsApiConnectionError as e:
        return {"status": "error", "error": f"Error de conexión: {e}"}
    except Exception as e:
        return {"status": "error", "error": f"Error inesperado: {e}"}


def send_message(chat_id, text):
    """
    Envía un mensaje al usuario usando la API de Telegram.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    return jsonify({"status": "success", "telegram_response": response.json()}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
