from firebase_admin import messaging

async def send_push(token, title, body, data):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data,
        token=token,
    )
    messaging.send(message)
