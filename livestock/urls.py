from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FarmViewSet,
    LabourerViewSet,
    LivestockViewSet,
    HealthRecordViewSet,
    AMURecordViewSet,
    FeedRecordViewSet,
    YieldRecordViewSet,
    DrugViewSet, # New
    AMUInsightsViewSet, # New
    FeedViewSet,
)
from .views_insights import (
    FeedInsightsViewSet,
    YieldInsightsViewSet,
)

router = DefaultRouter()
router.register(r"farms", FarmViewSet, basename="farm")
router.register(r"labourers", LabourerViewSet, basename="labourer")
router.register(r"livestock", LivestockViewSet, basename="livestock")
router.register(r"health-records", HealthRecordViewSet, basename="healthrecord")
router.register(r"amu-records", AMURecordViewSet, basename="amurecord")
router.register(r"feed-records", FeedRecordViewSet, basename="feedrecord")
router.register(r"yield-records", YieldRecordViewSet, basename="yieldrecord")
router.register(r"drugs", DrugViewSet, basename="drug") # New
router.register(r"amu-insights", AMUInsightsViewSet, basename="amu-insight") # New
router.register(r"feeds", FeedViewSet, basename="feed")
router.register(r"feed-insights", FeedInsightsViewSet, basename="feed-insight")
router.register(r"yield-insights", YieldInsightsViewSet, basename="yield-insight")

urlpatterns = [
    path("", include(router.urls)),
]
