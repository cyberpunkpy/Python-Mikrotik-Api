"""
Script para probar que la libreria funcione bien con la api del mikrotik que se este usando
"""

import routeros_api

# Configuración de conexión
mikrotik_host = "192.168.88.1" # ip del mikrotik
mikrotik_username = "apipython"  # Cambia por tu usuario
mikrotik_password = "Admin12345."  # Cambia por tu contraseña

try:
    # Conexión al MikroTik
    connection = routeros_api.RouterOsApiPool(
        mikrotik_host,
        username=mikrotik_username,
        password=mikrotik_password,
        port=8728, # puerto de servicio de la api del mikrotik
        plaintext_login=True
    )
    api = connection.get_api()

    # Obtener el address list (  para verificar que funciona bien con la api y no hay fallas )
    address_list = api.get_resource('/ip/firewall/address-list')
    items = address_list.get()
    for item in items:
        print(f"IP: {item['address']}, List: {item['list']}, Comment: {item.get('comment', 'N/A')}")

    connection.disconnect()
except routeros_api.exceptions.RouterOsApiConnectionError as e:
    print(f"Error de conexión: {e}")
except Exception as e:
    print(f"Error inesperado: {e}")
