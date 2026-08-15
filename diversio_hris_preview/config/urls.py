from django.urls import path

from preview import views

urlpatterns = [
    path("", views.import_preview, name="import-preview"),
]
