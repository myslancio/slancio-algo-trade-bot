import traceback
from alerts.models import ArchitectureError
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

class EnterpriseResilienceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, req):
        try:
            response = self.get_response(req)
            return response
        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            
            # Use try-except to avoid recursive failures if database is down
            try:
                ArchitectureError.objects.create(
                    error_message=error_msg,
                    traceback=tb,
                    component='Django Middleware'
                )
            except:
                logger.error("Failed to log error to database. Database might be down.")
            
            logger.error(f"Architecture Error Caught: {error_msg}")
            
            return JsonResponse({
                "status": "error",
                "message": "An internal architecture error occurred. It has been logged for auto-repair.",
                "error_id": "ARCH-ERR-500"
            }, status=500)
