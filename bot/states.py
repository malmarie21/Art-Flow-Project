from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    intro = State()
    gender = State()
    age = State()
    experience = State()
    pre_lesson = State()


class LessonStates(StatesGroup):
    block1 = State()
    block2 = State()
    block3 = State()
    q1 = State()
    q1_feedback = State()
    block4 = State()
    q2 = State()
    q2_feedback = State()
    block5 = State()
    q3 = State()
    q3_feedback = State()
    block6 = State()
    q4 = State()
    q4_feedback = State()
    post_q4_intro = State()
    q5 = State()
    q5_feedback = State()
    q6 = State()
    q6_feedback = State()
    summary = State()


class SurveyStates(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()
    q6 = State()
    q7 = State()
    q8 = State()
    awaiting_open_comment = State()
    finished = State()
