from django.db import models


class Message(models.Model):
    """Model For Wallet Message."""
    messsage = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)
