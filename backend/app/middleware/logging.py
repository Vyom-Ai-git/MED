import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
from app.core.config import settings

logger = logging.getLogger("app.middleware.request")

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Track request ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        
        # Try to parse token to fetch user_id and organization_id (if authenticated)
        user_id = None
        organization_id = None
        
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decoded subject is usually user_id
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET,
                    algorithms=[settings.JWT_ALGORITHM]
                )
                user_id = payload.get("sub")
                # We can also store org_id in token or fetch it inside routes.
                # In Phase 0, if it is in the token we read it, else it is resolved in services.
                organization_id = payload.get("org_id")
            except jwt.PyJWTError:
                pass
                
        # Handle request
        response = None
        error_msg = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            error_msg = str(e)
            status_code = 500
            raise e
        finally:
            duration = time.time() - start_time
            
            # Log the request lifecycle
            extra_data = {
                "request_id": request_id,
                "endpoint": f"{request.method} {request.url.path}",
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
            }
            if user_id:
                extra_data["user_id"] = user_id
            if organization_id:
                extra_data["organization_id"] = organization_id
            if error_msg:
                extra_data["error"] = error_msg
                
            # Log at appropriate level
            if status_code >= 500:
                logger.error(f"Request failed: {request.method} {request.url.path}", extra=extra_data)
            elif status_code >= 400:
                logger.warning(f"Request warning: {request.method} {request.url.path}", extra=extra_data)
            else:
                logger.info(f"Request completed: {request.method} {request.url.path}", extra=extra_data)
                
        # Inject request-id in response headers
        if response:
            response.headers["x-request-id"] = request_id
            
        return response
