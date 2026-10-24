
from django.urls import path
from . import views

app_name = "boxes"


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("boxes/", views.box_list, name="box_list"),
    path("boxes/add/", views.box_create, name="box_create"),
    path("boxes/<int:pk>/edit/", views.box_edit, name="box_edit"),
    path(
        "boxes/<int:pk>/deactivate/",
        views.box_deactivate,
        name="box_deactivate",
    ),
    path("recommend/", views.recommend_box_page, name="recommend_page"),

    # Existing JSON endpoint
    path("api/recommend/", views.recommend_box_view, name="recommend_api"),
]
