from fastapi import HTTPException, status


class HootLineException(HTTPException):
    status_code = 500
    detail = "Вышла ошибочка, мы уже думаем над её решением!"

    def __init__(self):
        super().__init__(status_code=self.status_code, detail=self.detail)


class HootLineExceptionDynamic(HTTPException):
    status_code = 500
    detail = "Вышла ошибочка, мы уже думаем над её решением!"

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class UserNameAlreadyExistsException(HootLineException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь с таким username уже существует"


class UserEmailAlreadyExistsException(HootLineException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь с таким email уже существует"


class TokenExpiredException(HootLineException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Срок действия токена истек"


class TokenAbsentException(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Токен отсутствует")


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


class EmailOrUsernameWasNotFound(HootLineExceptionDynamic):
    def __init__(self):
        super().__init__(status_code=404, detail="Пользователь не найден")


class InvalidPassword(HootLineExceptionDynamic):
    def __init__(self):
        super().__init__(status_code=401, detail="Неверный пароль")


class FailedToGetUserRoles(HootLineExceptionDynamic):
    def __init__(self):
        super().__init__(status_code=400, detail="Не удалось получить роли пользователя")


class FailedTGetDataFromDatabase(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Не удалось получить данные из базы"


class CategoryWithTheSameNameAlreadyExists(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ErrorCreatingCategory(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при создании категории"


class ErrorGettingCategories(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при получении категорий"


class CategoryNotFound(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Категория не найдена"


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


class CategoryNotFoundException(HootLineExceptionDynamic):
    def __init__(self, category_id: int):
        detail = f"Категория с id {category_id} не найдена"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ValidationErrorException(HootLineExceptionDynamic):
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


class SubQuestionNotFound(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Под-вопрос не найден"


class CouldNotGetAnswerToQuestion(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Не удалось получить ответ на вопрос"


class ParentCategoryNotFound(HootLineException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Родительская категория не найдена"


class CategoryWithSameNameAlreadyExists(HootLineExceptionDynamic):
    def __init__(self, category_name: str):
        detail = f"Категория с именем '{category_name}' уже существует."
        super().__init__(status_code=400, detail=detail)


class FailedToUpdateSubcategories(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Не удалось обновить подкатегории"


class ErrorGettingUser(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при получении пользователя"


class MissingTokenException(HootLineExceptionDynamic):
    def __init__(self, detail="Токен отсутствует или недействителен"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForASubquestionYouMustSpecifyParentQuestionId(HootLineExceptionDynamic):
    def __init__(self, detail="Для подвопроса необходимо указать parent_question_id."):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class FailedToCreateQuestionDynamic(HootLineExceptionDynamic):
    def __init__(self, detail="Не удалось создать вопрос"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ParentQuestionIDNotFound(HootLineExceptionDynamic):
    def __init__(self, detail="Родительский вопрос с ID"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class IncorrectParentSubquestionIdValueNumberExpected(HootLineExceptionDynamic):
    def __init__(self, detail="Некорректное значение parent_subquestion_id, ожидается число"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ErrorCreatingSubquestion(HootLineExceptionDynamic):
    def __init__(self, detail="Ошибка при создании под-вопроса"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ErrorInGetQuestions(HootLineExceptionDynamic):
    def __init__(self, detail="Ошибка в get_questions"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ErrorInGetQuestionWithSubquestions(HootLineExceptionDynamic):
    def __init__(self, detail="Ошибка в get_question_with_subquestions"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class TheSubQuestionDoesNotBelongToTheSpecifiedMainQuestion(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Под-вопрос не принадлежит указанному основному вопросу"


class CannotDeleteSubQuestionWithNestedSubQuestions(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Невозможно удалить под-вопрос с вложенными под-вопросами"


class QuestionOrSubQuestionSuccessfullyDeleted(HootLineException):
    status_code = status.HTTP_202_ACCEPTED
    detail = "Вопрос или под-вопрос успешно удалены"


class ErrorWhenDeletingQuestion(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при удалении вопроса"


class SubQuestionSuccessfullyUpdated(HootLineException):
    status_code = status.HTTP_202_ACCEPTED
    detail = "Под-вопрос успешно обновлен"


class QuestionSuccessfullyUpdated(HootLineException):
    status_code = status.HTTP_202_ACCEPTED
    detail = "Вопрос успешно обновлен"


class ErrorWhenUpdatingQuestion(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при обновлении вопроса"


class InvalidRefreshToken(HootLineException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Неверный Refresh токен "


class RefreshTokenHasExpired(HootLineException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Срок действия токена обновления истек"


class TokenRedirectException(Exception):
    def __init__(self, message: str, redirect_url: str):
        super().__init__(message)
        self.redirect_url = redirect_url


class EmptyPasswordError(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Пароль не может быть пустым и должен содержать не менее 6 символов"


class EmptyUserNameOrEmailError(HootLineException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Имя пользователя или почта не введены"


class DatabaseConnectionLost(HootLineException):
    """Исключение при потере соединения с базой данных."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE  # 503: Сервис недоступен
    detail = "Соединение с базой данных потеряно."


class DatabaseExceptions(HootLineExceptionDynamic):
    """Обработка общих ошибок базы данных."""
    def __init__(self, e: str):
        detail = "Внутренняя ошибка сервера"
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)