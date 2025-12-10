from rest_framework import viewsets
from .models import Metric
from .serializers import MetricSerializer

class MetricViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Metric.objects.all().order_by('timestamp')
    serializer_class = MetricSerializer
