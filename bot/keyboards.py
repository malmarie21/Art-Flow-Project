from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def inline_options(prefix: str, options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=f"{prefix}:{value}")]
            for text, value in options
        ]
    )


def gender_keyboard() -> InlineKeyboardMarkup:
    return inline_options(
        "gender",
        [("Женский", "female"), ("Мужской", "male"), ("Предпочитаю не указывать", "unknown")],
    )


def age_keyboard() -> InlineKeyboardMarkup:
    return inline_options(
        "age",
        [("до 20", "under_20"), ("20–29", "20_29"), ("30–39", "30_39"), ("40+", "40_plus")],
    )


def experience_keyboard() -> InlineKeyboardMarkup:
    return inline_options(
        "exp",
        [
            ("Почти не изучал(а)", "almost_none"),
            ("Иногда интересуюсь", "sometimes"),
            ("Изучал(а) системно", "systematic"),
            ("Профессионально связан(а)", "professional"),
        ],
    )


def answer_keyboard(options: list[tuple[str, str]], question_number: int) -> InlineKeyboardMarkup:
    return inline_options(f"lesson_q{question_number}", options)


def survey_keyboard(question_number: int, options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return inline_options(f"survey_q{question_number}", options)


def continue_to_survey_keyboard() -> InlineKeyboardMarkup:
    return inline_options("flow", [("➡ Перейти к опросу", "to_survey")])


def continue_keyboard() -> InlineKeyboardMarkup:
    return inline_options("flow", [("Продолжить", "continue")])


def start_lesson_keyboard() -> InlineKeyboardMarkup:
    return inline_options("flow", [("Начать урок", "start_lesson")])


def lesson_action_keyboard(label: str, action: str) -> InlineKeyboardMarkup:
    return inline_options("flow", [(label, action)])

def open_comment_keyboard() -> InlineKeyboardMarkup:
    return inline_options("flow", [("Хочу добавить открытый комментарий", "add_comment")])
