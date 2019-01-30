from django.urls import include, path

from .views import create_report, view_detail, view_report

urlpatterns = [
    path('', create_report, name='create_report'),
    path('report/<int:pk>/', include([
        path('', view_report, name='report'),
        path('statement/<ticker_symbol>/', view_detail, name='detail'),
    ])),
]
