FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# system deps for psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# copy only users_service first (better caching)
COPY reviews_service/requirements.txt /app/reviews_service/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/reviews_service/requirements.txt

# now copy service code
COPY reviews_service /app/reviews_service

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "reviews_service.wsgi:app"]