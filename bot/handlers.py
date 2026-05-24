from __future__ import annotations

from dataclasses import dataclass

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from ab_logic import GROUP_CONTROL, GROUP_TEST, assign_group
from db import Database
from keyboards import (
    age_keyboard,
    answer_keyboard,
    continue_keyboard,
    continue_to_survey_keyboard,
    experience_keyboard,
    gender_keyboard,
    lesson_action_keyboard,
    open_comment_keyboard,
    start_lesson_keyboard,
    survey_keyboard,
)
from states import LessonStates, OnboardingStates, SurveyStates


TEST_GREETING_IMAGE = "Контент для бота/М – знакомство.png"
TEST_PRE_LESSON_IMAGE = "Контент для бота/М – перед началом.png"
LESSON_BLOCK_1_COMMON_IMAGE = "Контент для бота/Блок 1 – 1 (общ).png"
LESSON_BLOCK_1_TEST_IMAGE = "Контент для бота/М – Блок 1 – 2.png"
LESSON_BLOCK_1_CONTROL_IMAGE = "Контент для бота/Блок 1 – 2.png"
LESSON_BLOCK_2_TEST_IMAGE = "Контент для бота/М – Блок 2 – 1.png"
LESSON_BLOCK_2_CONTROL_IMAGE = "Контент для бота/Блок 2 – 1.png"
LESSON_BLOCK_2_COMMON_IMAGE = "Контент для бота/Блок 2 – 2 (общ).png"
LESSON_BLOCK_3_TEST_IMAGE = "Контент для бота/М – Блок 3 – 1.png"
LESSON_BLOCK_3_CONTROL_IMAGE = "Контент для бота/Блок 3 – 1.png"
LESSON_BLOCK_3_COMMON_IMAGE = "Контент для бота/Блок 3 – 2 (общ).png"
LESSON_BLOCK_4_TEST_IMAGE = "Контент для бота/М – Блок 4 – 1.png"
LESSON_BLOCK_4_CONTROL_IMAGE = "Контент для бота/Блок 4 – 1.png"
LESSON_BLOCK_4_COMMON_IMAGE = "Контент для бота/Блок 4 – 2 (общ).png"
LESSON_BLOCK_5_TEST_IMAGE = "Контент для бота/М – Блок 5.png"
LESSON_BLOCK_5_CONTROL_IMAGE = "Контент для бота/Блок 5.png"
LESSON_BLOCK_6_TEST_IMAGE = "Контент для бота/М – Блок 6.png"
LESSON_BLOCK_6_CONTROL_IMAGE = "Контент для бота/Блок 6.png"
QUESTION_1_TEST_CORRECT_IMAGE = "Контент для бота/М – В1 – Прав.png"
QUESTION_1_TEST_WRONG_IMAGE = "Контент для бота/М – В1 – Непр.png"
QUESTION_2_TEST_CORRECT_IMAGE = "Контент для бота/М – В2 – Прав.png"
QUESTION_2_TEST_WRONG_IMAGE = "Контент для бота/М – В2 – Непр.png"
QUESTION_3_TEST_CORRECT_IMAGE = "Контент для бота/М – В3 – Прав.png"
QUESTION_3_TEST_WRONG_IMAGE = "Контент для бота/М – В3 – Непр.png"
QUESTION_4_TEST_CORRECT_IMAGE = "Контент для бота/М – В4 – Прав.png"
QUESTION_4_TEST_WRONG_IMAGE = "Контент для бота/М – В4 – Неправ.png"
QUESTION_5_TEST_FEEDBACK_IMAGE = "Контент для бота/М – В5 – Прав и Неправ.png"
QUESTION_6_TEST_FEEDBACK_IMAGE = "Контент для бота/М – В6 – Прав и Неправ.png"
SUMMARY_ALL_CORRECT_TEST_IMAGE = "Контент для бота/М – Итог – всё прав.png"
SUMMARY_NOT_ALL_CORRECT_TEST_IMAGE = "Контент для бота/М – Итог – есть ошиб.png"
FINAL_TEST_IMAGE = "Контент для бота/М – конец.png"

@dataclass(frozen=True, slots=True)
class LessonQuestion:
    number: int
    text: str
    options: list[tuple[str, str]]
    correct_option: str
    success_test_text: str
    success_control_text: str
    failure_test_text: str
    failure_control_text: str
    test_correct_image: str | None = None
    test_wrong_image: str | None = None


LESSON_QUESTIONS = [
    LessonQuestion(
        number=1,
        text=(
            "<b>Вопрос 1 из 6</b>\n"
            "Что важнее для импрессиониста?\n"
            "А) Точное сходство с объектом\n"
            "В) Передача устойчивых характеристик\n"
            "С) Передача ощущения момента"
        ),
        options=[
            ("А) Точное сходство с объектом", "A"),
            ("В) Передача устойчивых характеристик", "B"),
            ("С) Передача ощущения момента", "C"),
        ],
        correct_option="C",
        success_test_text="Верно! ✅",
        success_control_text="Верно ✅ Импрессионисты стремились передать ощущение мгновения – свет, воздух и настроение момента.",
        failure_test_text=(
            "Не совсем так.\n"
            "Правильный ответ: <b>передача ощущения момента</b>"
        ),
        failure_control_text=(
            "Не совсем так.\n"
            "Правильный ответ: <b>передача ощущения момента</b>\n\n"
            "Ничего страшного – этот вопрос может вызывать сомнения. "
            "Импрессионисты старались передать впечатление от мгновения, а не точное сходство с объектом."
        ),
        test_correct_image=QUESTION_1_TEST_CORRECT_IMAGE,
        test_wrong_image=QUESTION_1_TEST_WRONG_IMAGE,
    ),
    LessonQuestion(
        number=2,
        text=(
            "<b>Вопрос 2 из 6</b>\n"
            "Почему импрессионисты не сглаживали мазки?\n"
            "А) Из-за нехватки времени\n"
            "В) Чтобы сохранить ощущение изменчивости\n"
            "С) Потому что это было проще"
        ),
        options=[
            ("А) Из-за нехватки времени", "A"),
            ("В) Чтобы сохранить ощущение изменчивости", "B"),
            ("С) Потому что это было проще", "C"),
        ],
        correct_option="B",
        success_test_text="Отлично! ✅",
        success_control_text="Именно так ✅ Несглаженные мазки помогают передать движение света и изменчивость атмосферы.",
        failure_test_text=(
            "Интересная версия, но ответ другой.\n"
            "Правильный ответ: <b>чтобы сохранить ощущение изменчивости</b>"
        ),
        failure_control_text=(
            "Интересная версия, но ответ другой.\n"
            "Правильный ответ: <b>чтобы сохранить ощущение изменчивости</b>\n\n"
            "Это нормально – у этого приёма не сразу заметен смысл. "
            "Живые мазки помогают показать, как свет и воздух меняются в моменте."
        ),
        test_correct_image=QUESTION_2_TEST_CORRECT_IMAGE,
        test_wrong_image=QUESTION_2_TEST_WRONG_IMAGE,
    ),
    LessonQuestion(
        number=3,
        text=(
            "<b>Вопрос 3 из 6</b>\n"
            "Какую роль играет зритель?\n"
            "А) Пассивно воспринимает готовую форму\n"
            "В) Достраивает образ в восприятии\n"
            "С) Получает точную визуальную инструкцию"
        ),
        options=[
            ("А) Пассивно воспринимает готовую форму", "A"),
            ("В) Достраивает образ в восприятии", "B"),
            ("С) Получает точную визуальную инструкцию", "C"),
        ],
        correct_option="B",
        success_test_text="Так и есть! ✅",
        success_control_text="Да ✅ Импрессионистская живопись работает так, что глаз зрителя сам собирает изображение из мазков.",
        failure_test_text=(
            "Есть неточность, давай посмотрим.\n"
            "Правильный ответ: <b>зритель достраивает образ в восприятии</b>"
        ),
        failure_control_text=(
            "Почти, но не совсем так.\n"
            "Правильный ответ: <b>зритель достраивает образ в восприятии</b>\n\n"
            "Наш глаз соединяет отдельные мазки в цельное изображение."
        ),
        test_correct_image=QUESTION_3_TEST_CORRECT_IMAGE,
        test_wrong_image=QUESTION_3_TEST_WRONG_IMAGE,
    ),
    LessonQuestion(
        number=4,
        text=(
            "<b>Вопрос 4 из 6</b>\n"
            "Почему импрессионизм вызвал сопротивление?\n"
            "А) Он нарушал академические нормы\n"
            "В) Он был технически слабым\n"
            "С) Он изображал только природу"
        ),
        options=[
            ("А) Он нарушал академические нормы", "A"),
            ("В) Он был технически слабым", "B"),
            ("С) Он изображал только природу", "C"),
        ],
        correct_option="A",
        success_test_text="Правильно! ✅",
        success_control_text="Правильно ✅ Импрессионисты нарушали академические правила, поэтому их работы вызывали много критики.",
        failure_test_text=(
            "Такое предположение вполне понятно.\n"
            "Но правильный ответ: <b>он нарушал академические нормы</b>"
        ),
        failure_control_text=(
            "Такое предположение вполне понятно.\n"
            "Но правильный ответ: <b>он нарушал академические нормы</b>\n\n"
            "Импрессионисты писали свободно и иначе работали со светом, что противоречило академическим правилам."
        ),
        test_correct_image=QUESTION_4_TEST_CORRECT_IMAGE,
        test_wrong_image=QUESTION_4_TEST_WRONG_IMAGE,
    ),
    LessonQuestion(
        number=5,
        text=(
            "<b>Вопрос 5 из 6:</b>\n"
            "Что лучше всего объясняет, почему мазки у импрессионистов остаются видимыми?\n"
            "А) Художники стремились ускорить процесс и не прорабатывали детали\n"
            "В) Это способ передать ощущение света и движения, которое зритель «собирает» сам\n"
            "С) Они не владели техникой гладкой живописи"
        ),
        options=[
            ("А) Художники стремились ускорить процесс и не прорабатывали детали", "A"),
            ("В) Это способ передать ощущение света и движения, которое зритель «собирает» сам", "B"),
            ("С) Они не владели техникой гладкой живописи", "C"),
        ],
        correct_option="B",
        success_test_text="Верно! ✅",
        success_control_text=(
            "Верно! ✅\n"
            "Видимые мазки – это приём: зритель сам объединяет их в цельный образ и ощущение света."
        ),
        failure_test_text=(
            "Есть неточность.\n"
            "Правильный ответ: <b>видимые мазки – это способ передать свет и движение, "
            "которые зритель «собирает» сам</b>"
        ),
        failure_control_text=(
            "Есть неточность.\n"
            "Правильный ответ: <b>видимые мазки – это способ передать свет и движение, "
            "которые зритель «собирает» сам</b>"
        ),
        test_correct_image=QUESTION_5_TEST_FEEDBACK_IMAGE,
        test_wrong_image=QUESTION_5_TEST_FEEDBACK_IMAGE,
    ),
    LessonQuestion(
        number=6,
        text=(
            "<b>Вопрос 6 из 6:</b>\n"
            "Если сравнить академическую живопись и импрессионизм, что меняется в роли зрителя?\n"
            "А) Зритель просто рассматривает готовое, детально проработанное изображение\n"
            "В) Зритель становится более активным: он сам «достраивает» изображение из мазков\n"
            "С) Роль зрителя не меняется"
        ),
        options=[
            ("А) Зритель просто рассматривает готовое, детально проработанное изображение", "A"),
            ("В) Зритель становится более активным: он сам «достраивает» изображение из мазков", "B"),
            ("С) Роль зрителя не меняется", "C"),
        ],
        correct_option="B",
        success_test_text="Всё так! ✅",
        success_control_text=(
            "Всё так! ✅\n"
            "В импрессионизме зритель активнее: он сам «собирает» изображение из мазков."
        ),
        failure_test_text=(
            "Не совсем так.\n"
            "Правильный ответ: <b>зритель становится активнее и сам «собирает» изображение из мазков</b>"
        ),
        failure_control_text=(
            "Не совсем так.\n"
            "Правильный ответ: <b>зритель становится более активным и достраивает изображение</b>"
        ),
        test_correct_image=QUESTION_6_TEST_FEEDBACK_IMAGE,
        test_wrong_image=QUESTION_6_TEST_FEEDBACK_IMAGE,
    ),
]


SURVEY_SCALE_OPTIONS = [
    ("1 - совсем не согласен(на)", "1"),
    ("2", "2"),
    ("3", "3"),
    ("4", "4"),
    ("5", "5"),
    ("6", "6"),
    ("7", "7"),
    ("8", "8"),
    ("9", "9"),
    ("10 - полностью согласен(на)", "10"),
]

SURVEY_QUESTIONS = [
    ("Я чувствовал(а), что меня поддерживают во время прохождения урока", SURVEY_SCALE_OPTIONS),
    ("В целом взаимодействовать с ботом было приятно", SURVEY_SCALE_OPTIONS),
    ("Иногда возникало ощущение более живого взаимодействия", SURVEY_SCALE_OPTIONS),
    ("Взаимодействие ощущалось живым, а не формальным", SURVEY_SCALE_OPTIONS),
    ("Мне было комфортно проходить урок", SURVEY_SCALE_OPTIONS),
    ("Я не переживал(а), что могу ошибиться", SURVEY_SCALE_OPTIONS),
    ("Бот выглядел дружелюбным", SURVEY_SCALE_OPTIONS),
    ("Я бы не против(а) пройти что-то подобное ещё раз", SURVEY_SCALE_OPTIONS),
]


def build_router(db: Database, lumi_image_id: str | None) -> Router:
    local_router = Router()

    def display_name(from_user) -> str:
        full_name = (from_user.full_name or "").strip()
        if full_name:
            return full_name.split()[0]
        username = (from_user.username or "").strip()
        if username:
            return username
        return "друг"

    def pluralize_questions(count: int) -> str:
        remainder_10 = count % 10
        remainder_100 = count % 100
        if remainder_10 == 1 and remainder_100 != 11:
            return "вопрос"
        if remainder_10 in {2, 3, 4} and remainder_100 not in {12, 13, 14}:
            return "вопроса"
        return "вопросов"

    async def send_photo(message: Message, path: str, caption: str | None = None, reply_markup=None) -> None:
        await message.answer_photo(photo=FSInputFile(path), caption=caption, reply_markup=reply_markup)

    async def send_photo_pair(
        message: Message,
        first_path: str,
        second_path: str,
        caption: str,
        button_label: str,
        button_action: str,
    ) -> None:
        await message.answer_media_group(
            media=[
                InputMediaPhoto(media=FSInputFile(first_path)),
                InputMediaPhoto(media=FSInputFile(second_path), caption=caption),
            ]
        )
        await message.answer("Когда будешь готов(а), нажми кнопку ниже.", reply_markup=lesson_action_keyboard(button_label, button_action))

    async def send_single_image_block(
        message: Message,
        state: FSMContext,
        telegram_id: int,
        image_path: str,
        text: str,
        button_label: str,
        button_action: str,
        next_state,
    ) -> None:
        await send_photo(
            message,
            image_path,
            text,
            reply_markup=lesson_action_keyboard(button_label, button_action),
        )
        await db.log_event(telegram_id, f"{button_action}_image_shown")
        await state.set_state(next_state)

    def lesson_variant_path(user_group: str, test_path: str, control_path: str) -> str:
        return test_path if user_group == GROUP_TEST else control_path

    async def send_lesson_block_1(message: Message, state: FSMContext, user_group: str, telegram_id: int) -> None:
        await send_photo_pair(
            message,
            LESSON_BLOCK_1_COMMON_IMAGE,
            lesson_variant_path(user_group, LESSON_BLOCK_1_TEST_IMAGE, LESSON_BLOCK_1_CONTROL_IMAGE),
            (
                "До середины XIX века художники работали медленно, в мастерских, при стабильном освещении. "
                "Картины создавались постепенно, с тщательной прорисовкой деталей. Такой подход считался признаком мастерства.\n\n"
                "Но со временем художники начали сомневаться: "
                "а действительно ли точность – главное в искусстве?"
            ),
            "Разобраться",
            "lesson_block_2",
        )
        await db.log_event(telegram_id, "lesson_block_1_image_1_shown")
        await db.log_event(telegram_id, "lesson_block_1_image_2_shown")
        await state.set_state(LessonStates.block1)

    async def send_lesson_block_2(message: Message, state: FSMContext, user_group: str, telegram_id: int) -> None:
        await send_photo_pair(
            message,
            lesson_variant_path(user_group, LESSON_BLOCK_2_TEST_IMAGE, LESSON_BLOCK_2_CONTROL_IMAGE),
            LESSON_BLOCK_2_COMMON_IMAGE,
            (
                "XIX век меняет ритм жизни: города растут, появляются поезда, улицы наполняются движением. "
                "Мир становится быстрее.\n\n"
                "Художники чувствуют: прежние способы изображения не передают это ощущение. "
                "Им становится важно показать не форму объекта, а впечатление от него."
            ),
            "Что значит впечатление?",
            "lesson_block_3",
        )
        await db.log_event(telegram_id, "lesson_block_2_image_1_shown")
        await db.log_event(telegram_id, "lesson_block_2_image_2_shown")
        await state.set_state(LessonStates.block2)

    async def send_lesson_block_3(message: Message, state: FSMContext, user_group: str, telegram_id: int) -> None:
        await send_photo_pair(
            message,
            lesson_variant_path(user_group, LESSON_BLOCK_3_TEST_IMAGE, LESSON_BLOCK_3_CONTROL_IMAGE),
            LESSON_BLOCK_3_COMMON_IMAGE,
            (
                "Импрессионизм – это попытка передать ощущение конкретного момента.\n\n"
                "Один и тот же пейзаж утром и вечером – это разные состояния света и воздуха. "
                "Художников интересует не то, как объект устроен, а то, как он ощущается здесь и сейчас.\n\n"
                "Отсюда – работа на открытом воздухе, быстрые мазки и отказ от сглаживания."
            ),
            "Попробовать ответить",
            "lesson_q1_start",
        )
        await db.log_event(telegram_id, "lesson_block_3_image_1_shown")
        await db.log_event(telegram_id, "lesson_block_3_image_2_shown")
        await state.set_state(LessonStates.block3)

    async def send_lesson_block_4(message: Message, state: FSMContext, user_group: str, telegram_id: int) -> None:
        await send_photo_pair(
            message,
            lesson_variant_path(user_group, LESSON_BLOCK_4_TEST_IMAGE, LESSON_BLOCK_4_CONTROL_IMAGE),
            LESSON_BLOCK_4_COMMON_IMAGE,
            (
                "Быстрые мазки появились не из-за нехватки навыка. Это был осознанный художественный выбор.\n\n"
                "Сглаженная поверхность могла «успокоить» изображение, но разрушала ощущение движения света. "
                "Даже незавершённость стала частью выразительности."
            ),
            "Ответить на вопрос",
            "lesson_q2_start",
        )
        await db.log_event(telegram_id, "lesson_block_4_image_1_shown")
        await db.log_event(telegram_id, "lesson_block_4_image_2_shown")
        await state.set_state(LessonStates.block4)

    async def send_lesson_block_5(message: Message, state: FSMContext, user_group: str, telegram_id: int) -> None:
        await send_single_image_block(
            message,
            state,
            telegram_id,
            lesson_variant_path(user_group, LESSON_BLOCK_5_TEST_IMAGE, LESSON_BLOCK_5_CONTROL_IMAGE),
            (
                "Вблизи картины импрессионистов выглядят как набор мазков и цветовых пятен. "
                "Издалека – они складываются в цельный образ.\n\n"
                "Зритель не просто смотрит. Он участвует в достраивании картины."
            ),
            "Проверить понимание",
            "lesson_q3_start",
            LessonStates.block5,
        )

    async def send_lesson_block_6(message: Message, state: FSMContext, user_group: str, telegram_id: int) -> None:
        await send_single_image_block(
            message,
            state,
            telegram_id,
            lesson_variant_path(user_group, LESSON_BLOCK_6_TEST_IMAGE, LESSON_BLOCK_6_CONTROL_IMAGE),
            (
                "Современники часто критиковали импрессионистов. Их картины называли незаконченными и слишком личными.\n\n"
                "Новое искусство нарушало академические ожидания. Но именно это стало его силой."
            ),
            "Продолжим",
            "lesson_q4_start",
            LessonStates.block6,
        )

    async def send_question(message: Message, state: FSMContext, telegram_id: int, question: LessonQuestion, next_state) -> None:
        await message.answer(
            question.text,
            reply_markup=answer_keyboard(question.options, question.number),
        )
        await db.log_event(telegram_id, "lesson_question_shown", str(question.number))
        await state.set_state(next_state)

    async def send_question_1(message: Message, state: FSMContext, telegram_id: int) -> None:
        await send_question(message, state, telegram_id, LESSON_QUESTIONS[0], LessonStates.q1)

    async def send_post_q4_intro(message: Message, state: FSMContext, telegram_id: int) -> None:
        await message.answer(
            (
                "Кажется, мы уже разобрались с основными идеями.\n"
                "Давай проверим, что получилось запомнить.\n"
                "Далее – пара вопросов по всему уроку."
            ),
            reply_markup=continue_keyboard(),
        )
        await db.log_event(telegram_id, "lesson_post_q4_intro_shown")
        await state.set_state(LessonStates.post_q4_intro)

    async def send_lesson_summary(message: Message, state: FSMContext, user_group: str, telegram_id: int, username: str) -> None:
        data = await state.get_data()
        correct_answers_count = int(data.get("correct_answers_count", 0))

        await db.set_lesson_completed(telegram_id, correct_answers_count)
        await db.log_event(telegram_id, "lesson_completed", str(correct_answers_count))

        if correct_answers_count == 6:
            if user_group == GROUP_TEST:
                await send_photo(
                    message,
                    SUMMARY_ALL_CORRECT_TEST_IMAGE,
                    (
                        "Отлично получилось!\n\n"
                        "Пожалуйста, оцени, насколько ты согласен(на) с утверждениями ниже по шкале от 1 до 10:\n"
                        "1 – совсем не согласен(на), 10 – полностью согласен(на)\n\n"
                        "Это очень важно для исследования."
                    ),
                    reply_markup=continue_to_survey_keyboard(),
                )
            else:
                await message.answer(
                    (
                        "Отлично получилось!\n\n"
                        "Ты ответил(а) на все вопросы правильно и уловил(а) ключевую идею импрессионизма – внимание к ощущению момента.\n\n"
                        "Пожалуйста, оцени, насколько ты согласен(на) с утверждениями ниже по шкале от 1 до 10:\n"
                        "1 – совсем не согласен(на), 10 – полностью согласен(на)\n\n"
                        "Это очень важно для исследования."
                    ),
                    reply_markup=continue_to_survey_keyboard(),
                )
        else:
            if user_group == GROUP_TEST:
                await send_photo(
                    message,
                    SUMMARY_NOT_ALL_CORRECT_TEST_IMAGE,
                    (
                        f"{username}, спасибо за прохождение урока!\n\n"
                        f"Ты ответил(а) правильно на {correct_answers_count} {pluralize_questions(correct_answers_count)}.\n\n"
                        "Пожалуйста, оцени, насколько ты согласен(на) с утверждениями ниже по шкале от 1 до 10:\n"
                        "1 – совсем не согласен(на), 10 – полностью согласен(на)\n\n"
                        "Это очень важно для исследования."
                    ),
                    reply_markup=continue_to_survey_keyboard(),
                )
            else:
                await message.answer(
                    (
                        f"{username}, спасибо за прохождение урока!\n\n"
                        f"Ты ответил(а) правильно на {correct_answers_count} {pluralize_questions(correct_answers_count)}.\n\n"
                        "Ошибаться и размышлять – естественная часть обучения.\n"
                        "Ты прошёл(а) этот путь внимательно.\n\n"
                        "Пожалуйста, оцени, насколько ты согласен(на) с утверждениями ниже по шкале от 1 до 10:\n"
                        "1 – совсем не согласен(на), 10 – полностью согласен(на)\n\n"
                        "Это очень важно для исследования."
                    ),
                    reply_markup=continue_to_survey_keyboard(),
                )

        await state.set_state(LessonStates.summary)

    async def start_lesson_flow(message: Message, state: FSMContext, user_group: str, telegram_id: int) -> None:
        await db.set_lesson_started(telegram_id)
        await db.log_event(telegram_id, "lesson_started")
        await state.update_data(correct_answers_count=0, group=user_group)
        await send_lesson_block_1(message, state, user_group, telegram_id)

    async def send_start_intro(message: Message, username: str, user_group: str) -> None:
        text = (
            f"{username}, приятно познакомиться!\n\n"
            "Это бот с короткими уроками об искусстве.\n\n"
            "Перед началом задам три коротких вопроса – это нужно для исследования формата."
        )
        if user_group == GROUP_TEST:
            await message.answer_photo(
                photo=FSInputFile(TEST_GREETING_IMAGE),
                caption=text,
                reply_markup=continue_keyboard(),
            )
            return
        await message.answer(text, reply_markup=continue_keyboard())

    async def send_pre_lesson_message(message: Message, username: str, user_group: str) -> None:
        if user_group == GROUP_TEST:
            text = (
                f"Спасибо, {username}!\n\n"
                "Начнём урок.\n\n"
                "Если появятся вопросы – это нормально.\n"
                "Я буду рядом."
            )
            await message.answer_photo(
                photo=FSInputFile(TEST_PRE_LESSON_IMAGE),
                caption=text,
                reply_markup=start_lesson_keyboard(),
            )
            return
        text = (
            f"Спасибо, {username}!\n\n"
            "Начнём урок"
        )
        await message.answer(text, reply_markup=start_lesson_keyboard())

    async def ask_survey_question(callback: CallbackQuery, state: FSMContext, question_number: int) -> None:
        text, options = SURVEY_QUESTIONS[question_number - 1]
        await callback.message.answer(
            f"<b>Утверждение {question_number} из {len(SURVEY_QUESTIONS)}</b>\n\n{text}",
            reply_markup=survey_keyboard(question_number, options),
        )
        await db.log_event(callback.from_user.id, "survey_question_shown", str(question_number))
        await state.set_state(getattr(SurveyStates, f"q{question_number}"))

    async def send_final_thank_you(message: Message, telegram_id: int, username: str) -> None:
        user = await db.get_user(telegram_id)
        text = f"{username}, спасибо, что прошёл(а) урок и ответил(а) на вопросы – это важно для исследования."

        if user and user["group"] == GROUP_TEST:
            await message.answer_photo(
                photo=FSInputFile(FINAL_TEST_IMAGE),
                caption=text,
                reply_markup=open_comment_keyboard(),
            )
            return

        await message.answer(text, reply_markup=open_comment_keyboard())

    @local_router.message(F.text == "/start")
    async def cmd_start(message: Message, state: FSMContext) -> None:
        telegram_id = message.from_user.id
        username = display_name(message.from_user)
        user = await db.get_user(telegram_id)

        if not user:
            group = await assign_group(db)
            await db.create_user(telegram_id, username, group)
            await db.log_event(telegram_id, "user_assigned", group)
            user = await db.get_user(telegram_id)

        await db.log_event(telegram_id, "start_clicked")
        await state.clear()
        await state.update_data(group=user["group"])
        await send_start_intro(message, username, user["group"])
        await state.set_state(OnboardingStates.intro)

    @local_router.callback_query(OnboardingStates.intro, F.data == "flow:continue")
    async def onboarding_intro_continue(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.message.answer("Выбери свой пол:", reply_markup=gender_keyboard())
        await state.set_state(OnboardingStates.gender)
        await callback.answer()

    @local_router.callback_query(OnboardingStates.gender, F.data.startswith("gender:"))
    async def onboarding_gender(callback: CallbackQuery, state: FSMContext) -> None:
        value = callback.data.split(":", 1)[1]
        await db.update_user_profile(callback.from_user.id, gender=value)
        await db.log_event(callback.from_user.id, "onboarding_gender_answered", value)
        await callback.message.answer("Выбери свою возрастную группу:", reply_markup=age_keyboard())
        await state.set_state(OnboardingStates.age)
        await callback.answer()

    @local_router.callback_query(OnboardingStates.age, F.data.startswith("age:"))
    async def onboarding_age(callback: CallbackQuery, state: FSMContext) -> None:
        value = callback.data.split(":", 1)[1]
        await db.update_user_profile(callback.from_user.id, age_group=value)
        await db.log_event(callback.from_user.id, "onboarding_age_answered", value)
        await callback.message.answer("Какой у тебя опыт в изучении искусства?", reply_markup=experience_keyboard())
        await state.set_state(OnboardingStates.experience)
        await callback.answer()

    @local_router.callback_query(OnboardingStates.experience, F.data.startswith("exp:"))
    async def onboarding_experience(callback: CallbackQuery, state: FSMContext) -> None:
        value = callback.data.split(":", 1)[1]
        await db.update_user_profile(callback.from_user.id, art_experience=value)
        await db.log_event(callback.from_user.id, "onboarding_experience_answered", value)
        await db.log_event(callback.from_user.id, "onboarding_completed")
        data = await state.get_data()
        username = display_name(callback.from_user)
        await send_pre_lesson_message(callback.message, username, data["group"])
        await state.set_state(OnboardingStates.pre_lesson)
        await callback.answer()

    @local_router.callback_query(OnboardingStates.pre_lesson, F.data == "flow:start_lesson")
    async def onboarding_start_lesson(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await callback.answer()
        await start_lesson_flow(callback.message, state, data["group"], callback.from_user.id)

    @local_router.callback_query(LessonStates.block1, F.data == "flow:lesson_block_2")
    async def lesson_block_2(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await callback.answer()
        await send_lesson_block_2(callback.message, state, data["group"], callback.from_user.id)

    @local_router.callback_query(LessonStates.block2, F.data == "flow:lesson_block_3")
    async def lesson_block_3(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await callback.answer()
        await send_lesson_block_3(callback.message, state, data["group"], callback.from_user.id)

    @local_router.callback_query(LessonStates.block3, F.data == "flow:lesson_q1_start")
    async def lesson_q1_start(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await send_question_1(callback.message, state, callback.from_user.id)

    @local_router.callback_query(LessonStates.q1_feedback, F.data == "flow:continue")
    async def lesson_q1_continue(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await db.log_event(callback.from_user.id, "lesson_q1_continue_clicked")
        await callback.answer()
        await send_lesson_block_4(callback.message, state, data["group"], callback.from_user.id)

    @local_router.callback_query(LessonStates.block4, F.data == "flow:lesson_q2_start")
    async def lesson_q2_start(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await send_question(callback.message, state, callback.from_user.id, LESSON_QUESTIONS[1], LessonStates.q2)

    @local_router.callback_query(LessonStates.block5, F.data == "flow:lesson_q3_start")
    async def lesson_q3_start(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await send_question(callback.message, state, callback.from_user.id, LESSON_QUESTIONS[2], LessonStates.q3)

    @local_router.callback_query(LessonStates.block6, F.data == "flow:lesson_q4_start")
    async def lesson_q4_start(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await send_question(callback.message, state, callback.from_user.id, LESSON_QUESTIONS[3], LessonStates.q4)

    async def process_lesson_answer(
        callback: CallbackQuery,
        state: FSMContext,
        question: LessonQuestion,
    ) -> None:
        selected = callback.data.split(":", 1)[1]
        is_correct = selected == question.correct_option
        data = await state.get_data()
        group = data["group"]
        correct_answers_count = int(data.get("correct_answers_count", 0)) + int(is_correct)

        await db.save_answer(
            callback.from_user.id,
            question.number,
            question.text,
            selected,
            is_correct,
        )
        await db.log_event(
            callback.from_user.id,
            "lesson_question_answered",
            f"{question.number}:{selected}:{int(is_correct)}",
        )
        await state.update_data(correct_answers_count=correct_answers_count)
        await callback.answer()

        if is_correct:
            if group == GROUP_TEST:
                await send_photo(
                    callback.message,
                    question.test_correct_image,
                    question.success_test_text,
                    reply_markup=continue_keyboard(),
                )
            else:
                await callback.message.answer(
                    question.success_control_text,
                    reply_markup=continue_keyboard(),
                )
        else:
            if group == GROUP_TEST:
                await send_photo(
                    callback.message,
                    question.test_wrong_image,
                    question.failure_test_text,
                    reply_markup=continue_keyboard(),
                )
            else:
                await callback.message.answer(
                    question.failure_control_text,
                    reply_markup=continue_keyboard(),
                )

        feedback_state_map = {
            1: LessonStates.q1_feedback,
            2: LessonStates.q2_feedback,
            3: LessonStates.q3_feedback,
            4: LessonStates.q4_feedback,
            5: LessonStates.q5_feedback,
            6: LessonStates.q6_feedback,
        }
        await state.set_state(feedback_state_map[question.number])

    @local_router.callback_query(LessonStates.q1, F.data.startswith("lesson_q1:"))
    async def lesson_q1(callback: CallbackQuery, state: FSMContext) -> None:
        await process_lesson_answer(callback, state, LESSON_QUESTIONS[0])

    @local_router.callback_query(LessonStates.q2, F.data.startswith("lesson_q2:"))
    async def lesson_q2(callback: CallbackQuery, state: FSMContext) -> None:
        await process_lesson_answer(callback, state, LESSON_QUESTIONS[1])

    @local_router.callback_query(LessonStates.q3, F.data.startswith("lesson_q3:"))
    async def lesson_q3(callback: CallbackQuery, state: FSMContext) -> None:
        await process_lesson_answer(callback, state, LESSON_QUESTIONS[2])

    @local_router.callback_query(LessonStates.q4, F.data.startswith("lesson_q4:"))
    async def lesson_q4(callback: CallbackQuery, state: FSMContext) -> None:
        await process_lesson_answer(callback, state, LESSON_QUESTIONS[3])

    @local_router.callback_query(LessonStates.q5, F.data.startswith("lesson_q5:"))
    async def lesson_q5(callback: CallbackQuery, state: FSMContext) -> None:
        await process_lesson_answer(callback, state, LESSON_QUESTIONS[4])

    @local_router.callback_query(LessonStates.q6, F.data.startswith("lesson_q6:"))
    async def lesson_q6(callback: CallbackQuery, state: FSMContext) -> None:
        await process_lesson_answer(callback, state, LESSON_QUESTIONS[5])

    @local_router.callback_query(LessonStates.q2_feedback, F.data == "flow:continue")
    async def lesson_q2_continue(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await db.log_event(callback.from_user.id, "lesson_q2_continue_clicked")
        await callback.answer()
        await send_lesson_block_5(callback.message, state, data["group"], callback.from_user.id)

    @local_router.callback_query(LessonStates.q3_feedback, F.data == "flow:continue")
    async def lesson_q3_continue(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await db.log_event(callback.from_user.id, "lesson_q3_continue_clicked")
        await callback.answer()
        await send_lesson_block_6(callback.message, state, data["group"], callback.from_user.id)

    @local_router.callback_query(LessonStates.q4_feedback, F.data == "flow:continue")
    async def lesson_q4_continue(callback: CallbackQuery, state: FSMContext) -> None:
        await db.log_event(callback.from_user.id, "lesson_q4_continue_clicked")
        await callback.answer()
        await send_post_q4_intro(callback.message, state, callback.from_user.id)

    @local_router.callback_query(LessonStates.post_q4_intro, F.data == "flow:continue")
    async def lesson_post_q4_intro_continue(callback: CallbackQuery, state: FSMContext) -> None:
        await db.log_event(callback.from_user.id, "lesson_post_q4_intro_continue_clicked")
        await callback.answer()
        await send_question(callback.message, state, callback.from_user.id, LESSON_QUESTIONS[4], LessonStates.q5)

    @local_router.callback_query(LessonStates.q5_feedback, F.data == "flow:continue")
    async def lesson_q5_continue(callback: CallbackQuery, state: FSMContext) -> None:
        await db.log_event(callback.from_user.id, "lesson_q5_continue_clicked")
        await callback.answer()
        await send_question(callback.message, state, callback.from_user.id, LESSON_QUESTIONS[5], LessonStates.q6)

    @local_router.callback_query(LessonStates.q6_feedback, F.data == "flow:continue")
    async def lesson_q6_continue(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        username = display_name(callback.from_user)
        await db.log_event(callback.from_user.id, "lesson_q6_continue_clicked")
        await callback.answer()
        await send_lesson_summary(callback.message, state, data["group"], callback.from_user.id, username)

    @local_router.callback_query(F.data == "flow:to_survey")
    async def start_survey(callback: CallbackQuery, state: FSMContext) -> None:
        await db.set_survey_started(callback.from_user.id)
        await db.log_event(callback.from_user.id, "survey_started")
        await callback.answer()
        await ask_survey_question(callback, state, 1)

    async def process_survey_answer(
        callback: CallbackQuery,
        state: FSMContext,
        question_number: int,
    ) -> None:
        selected = callback.data.split(":", 1)[1]
        question_text, _ = SURVEY_QUESTIONS[question_number - 1]

        await db.save_survey_answer(
            callback.from_user.id,
            question_number,
            question_text,
            selected,
        )
        await db.log_event(
            callback.from_user.id,
            "survey_question_answered",
            f"{question_number}:{selected}",
        )
        await callback.answer()

        if question_number < len(SURVEY_QUESTIONS):
            await ask_survey_question(callback, state, question_number + 1)
            return

        await db.set_survey_completed(callback.from_user.id)
        await db.log_event(callback.from_user.id, "survey_completed")
        await db.log_event(callback.from_user.id, "flow_completed")
        username = display_name(callback.from_user)
        await send_final_thank_you(callback.message, callback.from_user.id, username)
        await state.set_state(SurveyStates.finished)

    @local_router.callback_query(SurveyStates.q1, F.data.startswith("survey_q1:"))
    async def survey_q1(callback: CallbackQuery, state: FSMContext) -> None:
        await process_survey_answer(callback, state, 1)

    @local_router.callback_query(SurveyStates.q2, F.data.startswith("survey_q2:"))
    async def survey_q2(callback: CallbackQuery, state: FSMContext) -> None:
        await process_survey_answer(callback, state, 2)

    @local_router.callback_query(SurveyStates.q3, F.data.startswith("survey_q3:"))
    async def survey_q3(callback: CallbackQuery, state: FSMContext) -> None:
        await process_survey_answer(callback, state, 3)

    @local_router.callback_query(SurveyStates.q4, F.data.startswith("survey_q4:"))
    async def survey_q4(callback: CallbackQuery, state: FSMContext) -> None:
        await process_survey_answer(callback, state, 4)

    @local_router.callback_query(SurveyStates.q5, F.data.startswith("survey_q5:"))
    async def survey_q5(callback: CallbackQuery, state: FSMContext) -> None:
        await process_survey_answer(callback, state, 5)

    @local_router.callback_query(SurveyStates.q6, F.data.startswith("survey_q6:"))
    async def survey_q6(callback: CallbackQuery, state: FSMContext) -> None:
        await process_survey_answer(callback, state, 6)

    @local_router.callback_query(SurveyStates.q7, F.data.startswith("survey_q7:"))
    async def survey_q7(callback: CallbackQuery, state: FSMContext) -> None:
        await process_survey_answer(callback, state, 7)

    @local_router.callback_query(SurveyStates.q8, F.data.startswith("survey_q8:"))
    async def survey_q8(callback: CallbackQuery, state: FSMContext) -> None:
        await process_survey_answer(callback, state, 8)

    @local_router.callback_query(SurveyStates.finished, F.data == "flow:add_comment")
    async def add_open_comment(callback: CallbackQuery, state: FSMContext) -> None:
        await db.log_event(callback.from_user.id, "survey_open_comment_requested")
        await callback.answer()
        await callback.message.answer("Можешь оставить свой комментарий об уроке, если хочешь.")
        await state.set_state(SurveyStates.awaiting_open_comment)

    @local_router.message(SurveyStates.awaiting_open_comment, F.text)
    async def save_open_comment(message: Message, state: FSMContext) -> None:
        comment_text = message.text.strip()
        if not comment_text:
            await message.answer("Если захочешь, можешь отправить комментарий текстом.")
            return

        await db.save_survey_open_comment(message.from_user.id, comment_text)
        await db.log_event(message.from_user.id, "survey_open_comment_saved")
        await message.answer("Спасибо!")
        await state.clear()

    @local_router.message(SurveyStates.awaiting_open_comment)
    async def save_open_comment_invalid(message: Message) -> None:
        await message.answer("Если захочешь, просто отправь комментарий текстом.")

    @local_router.message()
    async def fallback(message: Message) -> None:
        await message.answer("Используй /start, чтобы начать сценарий заново.")

    return local_router
