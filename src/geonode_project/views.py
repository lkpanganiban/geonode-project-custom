from django.shortcuts import render


def map_app_view(request):
    """Render the MapLibre SPA map application."""
    return render(request, "geonode_project/map_app.html")
