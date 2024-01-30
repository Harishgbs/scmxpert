import socket
import os
from dotenv import load_dotenv
load_dotenv()
PORT = int( os.getenv('Port'))
print(PORT)     
ADDR = (os.getenv("host"), PORT)
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("address=>",ADDR,"\nclient=>",client)
client.connect(ADDR)
while True:
    data = client.recv(1024).decode('utf-8')
    if not data:
        break
    from confluent_kafka import Producer
    producer_config={'bootstrap.servers':os.getenv('bootstrap_servers'),
                     'client.id': 'python-producer',
                     }
    producer = Producer(producer_config)
    send_data=producer.produce('learn',data)
    producer.flush() 
    producer.close()
    print(send_data)
    print("Received data from server:", data)
client.close()