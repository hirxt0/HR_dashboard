from django.contrib import admin
from .models import Metric

@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'timestamp', 'value')
    list_filter = ('name',)
    search_fields = ('name',)
