from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import logging
import asyncio

from app.logger.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()  # Начало измерения времени обработки запроса

        # Логируем запрос
        log_request_data = {
            "event": "request",
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
        }

        # Опционально логируем тело запроса (ограничивая размер)
        try:
            request_body = await request.body()
            if request_body:
                log_request_data["body"] = request_body.decode("utf-8")[:500]  # Логируем до 500 символов
        except Exception as e:
            log_request_data["body_error"] = f"Failed to read request body: {str(e)}"

        # Логируем запрос с сообщением
        logger.info("Incoming request", extra=log_request_data)

        try:
            response = await call_next(request)

            # Логируем ответ
            log_response_data = {
                "event": "response",
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }

            # Опционально логируем тело ответа (ограничивая размер)
            response_body = b""
            try:
                async for chunk in response.body_iterator:
                    response_body += chunk
                if response_body:
                    log_response_data["body"] = response_body.decode("utf-8")[:500]  # Логируем до 500 символов
            except Exception as e:
                log_response_data["body_error"] = f"Failed to read response body: {str(e)}"

            # Восстанавливаем тело ответа для дальнейшего использования
            async def body_generator():
                yield response_body

            response.body_iterator = body_generator()

            # Логируем ответ с сообщением
            logger.info("Response sent", extra=log_response_data)

            return response
        except Exception as e:
            # Логируем ошибку с сообщением
            logger.error("Error occurred", extra={
                "event": "error",
                "message": str(e),
                "method": request.method,
                "url": str(request.url),
            })
            return Response(content="Internal Server Error", status_code=500)
        finally:
            # Логируем время обработки запроса
            process_time = time.time() - start_time
            logger.info("Request handling time", extra={
                "event": "process_time",
                "method": request.method,
                "url": str(request.url),
                "process_time": process_time,
            })
