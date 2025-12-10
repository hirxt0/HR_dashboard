from django.db import models

# Create your models here.
from django.db import models

class Metric(models.Model):
    name = models.CharField(max_length=200)
    timestamp = models.DateTimeField()
    value = models.FloatField()

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.name} @ {self.timestamp}"
