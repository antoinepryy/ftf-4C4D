FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app ./app
ENV PYTHONUNBUFFERED=1
