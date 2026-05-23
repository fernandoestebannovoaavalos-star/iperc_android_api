from locust import HttpUser, task, between

class TrabajadorIPERC(HttpUser):
    wait_time = between(1, 3)  # espera entre 1 y 3 segundos entre tareas
    
    def on_start(self):
        """Login al iniciar cada usuario simulado"""
        self.client.post('/login', data={
            'dni': '42426208',
            'password': 'tu_password_aqui'  # ← pon tu contraseña real
        })
    
    @task(3)
    def ver_dashboard(self):
        self.client.get('/dashboard')
    
    @task(2)
    def ver_mis_registros(self):
        self.client.get('/mis-registros')
    
    @task(2)
    def nuevo_iperc(self):
        self.client.get('/iperc/nuevo')
    
    @task(1)
    def ver_pdf(self):
        self.client.get('/reportes/pdf/1')
    
    @task(1)
    def get_actividades(self):
        self.client.get('/iperc/get_actividades/1')