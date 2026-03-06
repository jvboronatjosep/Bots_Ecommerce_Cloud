# Usamos la imagen oficial de Playwright con Python para asegurar que los navegadores funcionen perfectamente
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos el archivo de dependencias
COPY requirements.txt .

# Instalamos gunicorn (servidor web profesional para producción) y las dependencias
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Instalamos los navegadores de Playwright y los datos de Camoufox
RUN playwright install chromium firefox
RUN python -m camoufox fetch

# Copiamos el resto del código al contenedor
COPY . .

# Comando para iniciar el servidor web usando Gunicorn en el puerto que Google Cloud asigne
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 server:app