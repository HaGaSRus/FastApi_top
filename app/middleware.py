from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time

from app.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()  # Начало измерения времени обработки запроса

        # Логируем запрос
        logger.info({
            "event": "request",
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            # "body": await request.body()  # Опционально, для логирования тела запроса
        })

        try:
            response = await call_next(request)

            # Логируем ответ
            logger.info({
                "event": "response",
                "status_code": response.status_code,
                "headers": dict(response.headers),
                # "body": b"".join([chunk async for chunk in response.body_iterator])  # Опционально, для логирования тела ответа
            })

            return response
        except Exception as e:
            # Логируем ошибку
            logger.error({
                "event": "error",
                "message": str(e),
                "method": request.method,
                "url": str(request.url),
            })
            return Response(content="Internal Server Error", status_code=500)
        finally:
            # Логируем время обработки запроса
            process_time = time.time() - start_time
            logger.info({
                "event": "process_time",
                "method": request.method,
                "url": str(request.url),
                "process_time": process_time,
            })
