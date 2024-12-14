# Flask-Telegram-MikroTik-API-Integration

Este proyecto nacio de mi necesidad de controlar y dar acceso a un sistema local
http que tengo montado y tiene un firewall que prefiero controlar manualmente, 
permite la gestión automatizada de solicitudes de acceso para técnicos a través de un formulario web para registrar las solicitudes.

Un bot de Telegram para que el administrador apruebe o rechace las solicitudes.

La API de MikroTik para añadir direcciones IP al address-list automáticamente cuando las solicitudes son aprobadas.


EL flujo del proyecto:
Formulario Web: Los técnicos envían su dirección IP y un comentario opcional desde un formulario web.
Notificación en Telegram: El bot de Telegram notifica al administrador sobre las nuevas solicitudes.

Gestión de solicitudes en Telegram:
Comando /approve <ID>: Aprueba la solicitud y agrega la IP al MikroTik.
Comando /reject <ID>: Rechaza la solicitud y la marca como rechazada en la base de datos.

Actualización automática en MikroTik: Las IP aprobadas se agregan automáticamente al address-list. 
( este address - list habilita la ip publica para que tengan acceso desde esa ip solicitada )

Requisitos

Python 3.8 o superior
Flask
SQLite
MikroTik RouterOS con API habilitada
Nginx (opcional para producción)
Certbot (para HTTPS con Let's Encrypt)

Librerías de Python

Instala las dependencias con: 
 - pip install flask sqlite3 requests routeros-api

Estructura

!- > app.py                  (Archivo principal de Flask)

!── init_db.py               (Script para inicializar la base de datos)

!── templates/

   !--> request_access.html  (Formulario web para solicitudes)

!── requirements.txt         (Dependencias de Python)

!── README.md                (Documentación)


Instalación

Clona este repositorio:

    git clone https://github.com/<tu-usuario>/<nombre-del-repo>.git
    cd <nombre-del-repo>
		
Instala las dependencias:

    pip install -r requirements.txt

Configura tu Mikrotik ( /ip service eneable api )

Inicializa la base de datos: (  Ejecuta el script init_db.py para crear la tabla requests: )

    python3 init_db.py


 Configura tu archivo app.py:

Cambia las siguientes variables:

		 TELEGRAM_TOKEN = "TU_TOKEN_DE_TELEGRAM"
		 ADMIN_CHAT_ID = 123456789  # Chat ID del administrador
		 MIKROTIK_HOST = "192.168.88.1"
		 MIKROTIK_USERNAME = "admin"
		 MIKROTIK_PASSWORD = "password"

     cambia tu nombre de address list ( en list name )
		 def add_ip_to_mikrotik(ip, list_name="aca el nombre de tu address list" ...
	 
EJECUTA LA APP.
	    
		 python3 app.py

Configura Nginx (opcional para producción): 
Redirige el tráfico al servidor Flask en el puerto 5000. Consulta la sección de configuración de Nginx más abajo.

USO: 

	https://tu-dominio/request_access

Accede al formulario y llena los campos para la solicitud de acceso.


Gestionar solicitudes

El bot de Telegram notificará al administrador con un mensaje como:

	🔔 Nueva solicitud de acceso:
		IP: 192.168.88.100
		Comentario: Acceso temporal
		ID de solicitud: 1
		Usa /approve 1 para aprobar o /reject 1 para rechazar.

		el (1) es el id que se va generando para cada solicitud en la BD 

 La ip sera agregada automaticamente en el address list. ( / approve ID )


 **************************************************************************

 CONFIGURAR NGINX

 Usa esta configuración para redirigir el tráfico HTTPS a Flask:
		
		server {
    		listen 443 ssl;
    		server_name <tu-dominio>;

    		ssl_certificate /etc/letsencrypt/live/<tu-dominio>/fullchain.pem;
    		ssl_certificate_key /etc/letsencrypt/live/<tu-dominio>/privkey.pem;

    		location / {
        		proxy_pass http://127.0.0.1:5000;
        		proxy_set_header Host $host;
        		proxy_set_header X-Real-IP $remote_addr;
        		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        		proxy_set_header X-Forwarded-Proto $scheme;
    }
	}

	server {
    listen 80;
    server_name <tu-dominio>;

    return 301 https://$host$request_uri;
	}

******************************************************************************

Inicializar Base de Datos: 
archivo init_db.py

	import sqlite3

	conn = sqlite3.connect("access_requests.db")
	cursor = conn.cursor()

	cursor.execute("""
	CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    comment TEXT,
    status TEXT DEFAULT 'pendiente',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)
	""")

	conn.commit()
	conn.close()


Contribuciones

Si deseas contribuir a este proyecto, envía un Pull Request o abre un Issue.


Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo LICENSE para más detalles.

 


		

	 		
 

 


 
	 





