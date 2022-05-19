FROM python:3.8-slim

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get -y upgrade &&  \
    apt-get install -qq -y \
    build-essential libpq-dev --no-install-recommends \
    python3-dev python3-pip python3-setuptools python3-wheel python3-cffi \
    && pip install --upgrade pip

WORKDIR /app

COPY ./requirements.txt ./app /app
# COPY app/ /app

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "7070", "--log-level", "debug"]
