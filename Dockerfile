FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 8192

ENV FLARESOLVERR_URL=http://flaresolverr:8191
ENV FLARESOLVERR_TIMEOUT=60000

CMD ["python", "server.py"]
