from app import create_app
from waitress import serve

app = create_app()

if __name__ == '__main__':
    serve(app, 
          host='0.0.0.0', 
          port=5000,
          ident='IPERC-Server',
          threads=16,          # hilos simultáneos
          connection_limit=100, # máx conexiones
          cleanup_interval=30,  # limpieza cada 30s
          channel_timeout=60)   # timeout por canal