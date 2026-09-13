"""
app.py
Punto de entrada de la API REST de Solsticio.

Local:       python app.py            (servidor de desarrollo en http://127.0.0.1:5000)
Producción:  gunicorn app:app         (Render)
Comandos:    flask --app app verificar-bd | flask --app app crear-admin
"""
from api import crear_app

app = crear_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
