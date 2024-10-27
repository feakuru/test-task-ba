import graphene

from apps.measurements.schema import Query as MeasurementsQuery


class Query(MeasurementsQuery, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query)
