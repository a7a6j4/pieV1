import pika
import json

def send_message(message: dict):
    # Remove password field if present
    message.pop('password', None)
    # Serialize to JSON and encode to bytes
    body = json.dumps(message).encode('utf-8')
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='hello', durable=True)
    channel.basic_publish(
        exchange='',
        routing_key='hello',
        body=body,
        properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent)
    )
    connection.close()