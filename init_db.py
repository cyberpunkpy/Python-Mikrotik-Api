import sqlite3
import os

def init_db():
    """
    Inicializa la base de datos con una tabla para solicitudes de acceso.
    """
    db_path = os.path.join(os.getcwd(), 'access_requests.db')
    conn = sqlite3.connect(db_path)  # Crea o conecta a la base de datos
    c = conn.cursor()

    # Crear la tabla para solicitudes de acceso
    c.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            comment TEXT,
            status TEXT DEFAULT 'pendiente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")

# Ejecutar la función
if __name__ == "__main__":
    init_db()
