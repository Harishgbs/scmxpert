FROM python:3.10.8-slim

WORKDIR /producer

COPY . .

RUN pip install python-dotenv confluent-kafka

CMD [ "python", "producer.py"]