from fastapi import HTTPException, status


class HootLineException(HTTPException):
    status_code = 500
    detail = ""

    def __init__(self):
        super().__init__(status_code=self.status_code, detail=self.detail)


class UserAlreadyExistsException(HootLineException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь уже существует"


class TokenExpiredException(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Срок действия токена истек"


class TokenAbsentException(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Токен отсутствует"


class IncorrectTokenFormatException(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный формат токена"


class UserIsNotPresentException(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED


class UserInCorrectEmailOrUsername(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Пользователь с таким именем пользователя не найден"


class UserCreated(HootLineException):
    status_code = status.HTTP_201_CREATED
    detail = "Пользователь успешно создан"

