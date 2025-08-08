"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from django.urls import path

# Import Socket.IO ASGI app
from home.socketio_server import socketio_asgi_app

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

# Mount Django at root and Socket.IO under /ws/socket.io/
# socketio server also handles the engine.io transport endpoints automatically
from asgiref.compatibility import guarantee_single_callable

class ProtocolRouter:
    def __init__(self, django_app, socketio_app):
        self.django_app = guarantee_single_callable(django_app)
        self.socketio_app = socketio_app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if path.startswith("/ws/socket.io") or path.startswith("/socket.io"):
            return await self.socketio_app(scope, receive, send)
        return await self.django_app(scope, receive, send)

application = ProtocolRouter(django_asgi_app, socketio_asgi_app)
