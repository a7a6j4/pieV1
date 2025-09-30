import pika
from ...brevo import send_email

def receive_message():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='hello', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='hello', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

def callback(ch, method, properties, body):

  send_email(body.get('email'), body.get('subject'), body.get('otp'))


  ch.basic_ack(delivery_tag=method.delivery_tag)

  print(body)