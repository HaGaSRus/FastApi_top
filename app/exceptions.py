from fastapi import HTTPException, status


class HootLineException(HTTPException):
    status_code = 500
    detail = ""

    def __init__(self):
        super().__init__(status_code=self.status_code, detail=self.detail)


class UserNameAlreadyExistsException(HootLineException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь с таким username уже существует"


class UserEmailAlreadyExistsException(HootLineException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь с таким email уже существует"


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
    detail = "Пользователь не существует"


class UserInCorrectEmailOrUsername(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Пользователь с такой почтой не найден"


class UserCreated(HootLineException):
    status_code = status.HTTP_201_CREATED
    detail = "Пользователь успешно создан"


class UserChangeRole(HootLineException):
    status_code = status.HTTP_200_OK
    detail = "Роли успешно обновлены"


class DeleteUser(HootLineException):
    status_code = status.HTTP_202_ACCEPTED
    detail = "Пользователь успешно удален"


class PasswordRecoveryInstructions(HootLineException):
    status_code = status.HTTP_200_OK
    detail = "Инструкции по восстановлению пароля отправлены на вашу почту."


class PasswordUpdatedSuccessfully(HootLineException):
    status_code = status.HTTP_200_OK
    detail = "Пароль успешно обновлен"


class UpdateUser(HootLineException):
    status_code = status.HTTP_200_OK
    detail = "Данные пользователя успешно обновлены"


class UserNotFoundException(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Пользователь не существует"


class PermissionDeniedException(HootLineException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "У вас нет прав для этого"
