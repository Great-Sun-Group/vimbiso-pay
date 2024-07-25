from django.db import models


class Message(models.Model):
    """Model For Wallet Message."""
    messsage = models.TextField()
