FROM python:3.11.4

WORKDIR /consumer

COPY . .

RUN pip install python-dotenv confluent-kafka pymongo

CMD [ "python", "consumer.py"]