from django.http import JsonResponse
from django.db import connection
from django.utils import timezone


def health_check(request):
    """API health status and database connectivity check."""
    db_status = "healthy"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return JsonResponse({
        "status": "online",
        "service": "CV Dhana Putra Mandiri Backend API",
        "timestamp": timezone.now().isoformat(),
        "database": db_status,
        "modules": {
            "inventory": "/api/inventory/",
            "finance": "/api/finance/",
            "hr": "/api/hr/",
            "reports": "/api/finance/reports/"
        }
    })
