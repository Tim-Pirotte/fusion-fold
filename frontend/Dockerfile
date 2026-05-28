# https://pythonspeed.com/articles/alpine-docker-python/
# We chose a hardened Debian based image instead
# https://hub.docker.com/hardened-images/catalog/dhi/python/guides
FROM dhi.io/python:3.10-dev AS build-stage

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM dhi.io/python:3.10 AS runtime-stage

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"
ENV FLASK_APP=src/main.py

WORKDIR /app

COPY --from=build-stage /app/venv /app/venv
COPY . .

CMD ["flask", "run", "--host", "0.0.0.0", "--port", "8000"]
