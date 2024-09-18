from fastapi import HTTPException, status


class HootLineException(HTTPException):
    status_code = 500
    detail = "Вышла ошибочка, мы уже думаем над её решением!"

    def __init__(self, status_code: int, detail: str, **kwargs):
        super().__init__(status_code=status_code, detail=detail, **kwargs)


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


class ErrorUpdatingUser(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при обновлении пользователя"


class EmailOrUsernameWasNotFound(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Пользователь с указанным email или username не найден"


class InvalidPassword(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный пароль"


class FailedToGetUserRoles(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Не удалось получить роли пользователя"


class FailedTGetDataFromDatabase(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Не удалось получить данные из базы"


class CategoryWithTheSameNameAlreadyExists(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Категория с таким именем уже существует"


class ErrorCreatingCategory(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при создании категории"


class ErrorGettingCategories(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при получении категорий"


class CategoryNotFound(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Категория не найдена"


class DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка целостности данных. Возможно, вопрос с таким текстом уже существует"


class FailedToCreateQuestion(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Не удалось создать вопрос"


class ParentQuestionNotFound(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Родительский вопрос не найден"


class FailedToCreateSubQuestion(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Не удалось создать под-вопрос"


class CategoryContainsSubcategoriesDeletionIsNotPossible(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Категория содержит подкатегории, удаление невозможно"


class FailedToDeleteCategory(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Не удалось удалить категорию"


class JSONDecodingError(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка декодирования JSON"


class InvalidDataFormat(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Неверный формат данных"


class CategoryNotFoundException(HootLineException):
    def __init__(self, category_id: int):
        detail = f"Категория с id {category_id} не найдена"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ValidationErrorException(HootLineException):
    def __init__(self, error_detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_detail)


class ErrorUpdatingCategories(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при обновлении категорий"


class FailedToUpdateCategories(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Не удалось обновить категории"


class QuestionNotFound(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Вопрос не найден"


class CouldNotGetAnswerToQuestion(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Не удалось получить ответ на вопрос"


class ParentCategoryNotFound(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Родительская категория не найдена"


class CategoryWithSameNameAlreadyExists(HootLineException):
    def __init__(self, name):
        detail = f"Категория с именем '{name}' уже существует"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)