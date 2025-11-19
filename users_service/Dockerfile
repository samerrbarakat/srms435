FROM python:3.11

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install flask flask-cors psycopg2-binary jwt

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]