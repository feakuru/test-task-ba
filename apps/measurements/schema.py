import graphene
from django.db.models import QuerySet, Sum
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from apps.measurements.models import (Location, MeasurementPoint,
                                      WaterFlowMeasurement)

_basic_search_filters = ['exact', 'icontains', 'istartswith']


class WaterFlowMeasurementType(DjangoObjectType):
    class Meta:
        model = WaterFlowMeasurement
        fields = '__all__'
        filter_fields = {
            'measurement_point': ['exact'],
            'measurement_point__name': _basic_search_filters,
            'measurement_point__location__name': _basic_search_filters,
            'measurement_point__location__address': _basic_search_filters,
            'timestamp': ['gt', 'lt', 'exact',]
        }
        interfaces = (graphene.relay.Node, )


class AggregatedWaterFlowMeasurementConnection(graphene.relay.Connection):
    class Meta:
        node = WaterFlowMeasurementType

    total_duration_ms = graphene.Int()
    total_volume_ml = graphene.Int()
    weighted_avg_temperature_min_celsius = graphene.Int()
    weighted_avg_temperature_avg_celsius = graphene.Int()
    weighted_avg_temperature_max_celsius = graphene.Int()

    def resolve_total_duration_ms(self, info, **kwargs):
        if isinstance(self.iterable, QuerySet):
            return int(self.iterable.aggregate(Sum('duration_ms'))['duration_ms__sum'])
        return int(sum([measurement.duration_ms for measurement in self.iterable]))

    def resolve_total_volume_ml(self, info, **kwargs):
        if isinstance(self.iterable, QuerySet):
            return int(self.iterable.aggregate(Sum('volume_ml'))['volume_ml__sum'])
        return int(sum([measurement.volume_ml for measurement in self.iterable]))

    def _resolve_weighted_avg_field(self, field_name, weight_name='volume_ml'):
        if isinstance(self.iterable, QuerySet):
            weight_sum = self.iterable.aggregate(Sum(weight_name))[f'{weight_name}__sum']
        else:
            weight_sum = sum(
                getattr(measurement, weight_name)
                for measurement in self.iterable
            )
        result = int(sum(
            getattr(measurement, field_name) * getattr(measurement, weight_name)
            for measurement in self.iterable
        ) / weight_sum)
        return result

    def resolve_weighted_avg_temperature_min_celsius(self, info, **kwargs):
        return self._resolve_weighted_avg_field('temperature_min_celsius')

    def resolve_weighted_avg_temperature_avg_celsius(self, info, **kwargs):
        return self._resolve_weighted_avg_field('temperature_avg_celsius')

    def resolve_weighted_avg_temperature_max_celsius(self, info, **kwargs):
        return self._resolve_weighted_avg_field('temperature_max_celsius')


class LocationType(DjangoObjectType):
    class Meta:
        model = Location
        fields = '__all__'
        filter_fields = {
            'name': _basic_search_filters,
            'address': _basic_search_filters,
        }
        interfaces = (graphene.relay.Node, )


class MeasurementPointType(DjangoObjectType):
    class Meta:
        model = MeasurementPoint
        fields = '__all__'
        filter_fields = {
            'name': _basic_search_filters,
            'location': ['exact'],
            'location__name': _basic_search_filters,
            'location__address': _basic_search_filters
        }
        interfaces = (graphene.relay.Node, )

    water_flow_measurements = graphene.relay.ConnectionField(
        AggregatedWaterFlowMeasurementConnection,
        start=graphene.DateTime(),
        end=graphene.DateTime(),
    )

    def resolve_water_flow_measurements(root, info, start, end):
        qs = WaterFlowMeasurement.objects.filter(measurement_point=root)
        if start:
            qs = qs.filter(timestamp__gte=start)
        if end:
            qs = qs.filter(timestamp__lte=end)
        return qs.order_by('timestamp')


class Query(graphene.ObjectType):
    location = graphene.relay.Node.Field(LocationType)
    all_locations = DjangoFilterConnectionField(LocationType)

