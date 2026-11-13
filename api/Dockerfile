FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GEOPORTAL_DATA_DIR=/datos

WORKDIR /app

# Las ruedas de pyogrio, rasterio y pyproj incluyen GDAL/PROJ: no se requiere GDAL del sistema.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

RUN useradd --system --uid 1000 --home /app geoportal \
    && mkdir -p /datos /geolibre && chown geoportal /datos /geolibre
USER geoportal
VOLUME ["/datos"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/salud').status==200 else 1)"

# Solo los proxies de redes privadas (nginx del contenedor web, nginx de Plesk) son de confianza:
# uvicorn recorre X-Forwarded-For de derecha a izquierda y toma la primera IP que no es de un proxy.
# Con "*" el cliente podría falsear su IP y saltarse el límite de intentos de ingreso.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"]
