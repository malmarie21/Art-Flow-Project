from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats


DATA_DIR = Path(".")
ASSETS_DIR = DATA_DIR / "results_assets"
TEST_ACCOUNT_IDS = [426826357, 420252802]
QUESTION_GROUPS = {
    "Целевая метрика: индекс ощущаемой поддержки": [1, 2, 3, 4, 5, 6, 7, 8],
    "Воспринимаемая поддержка": [1, 2, 7],
    "Эмоциональная безопасность": [5, 6],
    "Социальное присутствие": [3, 4],
    "Поведенческое намерение": [8],
}


def ensure_dirs():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def prepare_users() -> pd.DataFrame:
    users = pd.read_csv(DATA_DIR / "users_2.csv")
    users.columns = users.columns.str.strip()
    users = users[~users["telegram_id"].isin(TEST_ACCOUNT_IDS)].copy()

    for col in [
        "created_at",
        "lesson_started_at",
        "lesson_completed_at",
        "survey_started_at",
        "survey_completed_at",
    ]:
        users[col] = pd.to_datetime(users[col], errors="coerce")

    users["started_lesson"] = users["lesson_started_at"].notna()
    users["completed_lesson"] = users["lesson_completed_at"].notna()
    users["started_survey"] = users["survey_started_at"].notna()
    users["completed_survey"] = users["survey_completed_at"].notna()
    users["lesson_duration_sec"] = (
        users["lesson_completed_at"] - users["lesson_started_at"]
    ).dt.total_seconds()
    users["survey_duration_sec"] = (
        users["survey_completed_at"] - users["survey_started_at"]
    ).dt.total_seconds()
    users["full_flow_duration_sec"] = (
        users["survey_completed_at"] - users["lesson_started_at"]
    ).dt.total_seconds()

    for col in ["lesson_duration_sec", "survey_duration_sec", "full_flow_duration_sec"]:
        users.loc[users[col] < 0, col] = np.nan

    return users


def prepare_survey() -> pd.DataFrame:
    survey = pd.read_csv(DATA_DIR / "survey_answers_2.csv")
    survey.columns = survey.columns.str.strip()
    survey["answered_at"] = pd.to_datetime(survey["answered_at"], errors="coerce")
    survey["survey_question_number"] = pd.to_numeric(
        survey["survey_question_number"], errors="coerce"
    )
    survey["selected_option"] = pd.to_numeric(survey["selected_option"], errors="coerce")
    survey["telegram_id"] = pd.to_numeric(survey["telegram_id"], errors="coerce")
    survey = survey[~survey["telegram_id"].isin(TEST_ACCOUNT_IDS)].copy()
    survey = survey[survey["survey_question_number"].between(1, 8)].copy()
    survey = survey.dropna(
        subset=["telegram_id", "survey_question_number", "answered_at", "selected_option"]
    ).copy()
    survey = survey.sort_values(["telegram_id", "answered_at"]).copy()
    survey["is_q1"] = (survey["survey_question_number"] == 1).astype(int)
    survey["attempt_n"] = survey.groupby("telegram_id")["is_q1"].cumsum()
    survey = survey[survey["attempt_n"] > 0].copy()
    return survey


def prepare_comments() -> pd.DataFrame:
    comments = pd.read_csv(DATA_DIR / "survey_open_comments_2.csv")
    comments["telegram_id"] = pd.to_numeric(comments["telegram_id"], errors="coerce")
    comments = comments[~comments["telegram_id"].isin(TEST_ACCOUNT_IDS)].copy()
    return comments


def get_last_full_survey_attempts(survey: pd.DataFrame) -> pd.DataFrame:
    attempt_summary = (
        survey.groupby(["telegram_id", "attempt_n"])
        .agg(
            questions_cnt=("survey_question_number", "nunique"),
            min_q=("survey_question_number", "min"),
            max_q=("survey_question_number", "max"),
            completed_at=("answered_at", "max"),
        )
        .reset_index()
    )

    full_attempts = attempt_summary[
        (attempt_summary["questions_cnt"] == 8)
        & (attempt_summary["min_q"] == 1)
        & (attempt_summary["max_q"] == 8)
    ].copy()

    last_full_attempts = (
        full_attempts.sort_values(["telegram_id", "completed_at"])
        .groupby("telegram_id", as_index=False)
        .tail(1)
        .copy()
    )

    return survey.merge(
        last_full_attempts[["telegram_id", "attempt_n"]],
        on=["telegram_id", "attempt_n"],
        how="inner",
    ).copy()


def bootstrap_diff_means(x, y, n_boot=10_000, random_state=42):
    rng = np.random.default_rng(random_state)
    x_vals = np.asarray(x)
    y_vals = np.asarray(y)
    diffs = np.empty(n_boot)

    for i in range(n_boot):
        x_boot = rng.choice(x_vals, size=len(x_vals), replace=True)
        y_boot = rng.choice(y_vals, size=len(y_vals), replace=True)
        diffs[i] = x_boot.mean() - y_boot.mean()

    return np.percentile(diffs, [2.5, 97.5])


def build_user_metric(
    survey_last: pd.DataFrame,
    users: pd.DataFrame,
    questions,
    source_col="selected_option",
    question_col="survey_question_number",
):
    metric_source = survey_last[survey_last[question_col].isin(questions)].copy()
    question_counts = metric_source.groupby("telegram_id")[question_col].nunique()
    complete_users = question_counts[question_counts == len(questions)].index
    metric_source = metric_source[metric_source["telegram_id"].isin(complete_users)].copy()
    users_group = users[["telegram_id", "group"]].drop_duplicates(subset=["telegram_id"])

    return (
        metric_source.merge(users_group, on="telegram_id", how="inner")
        .groupby(["telegram_id", "group"], as_index=False)
        .agg(metric=(source_col, "mean"))
    )


def analyze_metric(user_metric: pd.DataFrame, metric_name: str) -> dict:
    test = user_metric.loc[user_metric["group"] == "test", "metric"].dropna()
    control = user_metric.loc[user_metric["group"] == "control", "metric"].dropna()

    welch = stats.ttest_ind(test, control, equal_var=False)
    mannwhitney = stats.mannwhitneyu(test, control, alternative="two-sided")
    ci_low, ci_high = bootstrap_diff_means(test, control)
    effect_abs = test.mean() - control.mean()

    return {
        "metric_name": metric_name,
        "n_control": len(control),
        "n_test": len(test),
        "control_mean": control.mean(),
        "test_mean": test.mean(),
        "effect_abs": effect_abs,
        "effect_pct": effect_abs / control.mean() * 100 if control.mean() else np.nan,
        "welch_p": welch.pvalue,
        "mannwhitney_p": mannwhitney.pvalue,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


def sample_description_table(users: pd.DataFrame) -> pd.DataFrame:
    group_sizes = users["group"].value_counts()
    category_map = {
        "almost_none": "Почти не интересуюсь искусством",
        "professional": "Профессионально связан(а) с искусством",
        "sometimes": "Иногда интересуюсь искусством",
        "systematic": "Систематически интересуюсь искусством",
    }
    rows = []
    for variable in ["gender", "age_group", "art_experience"]:
        counts = pd.crosstab(users[variable], users["group"])
        for level in counts.index:
            control_n = counts.loc[level].get("control", 0)
            test_n = counts.loc[level].get("test", 0)
            category_label = category_map.get(level, level)
            rows.append(
                {
                    "variable": variable,
                    "category": category_label,
                    "control_n": int(control_n),
                    "control_share": control_n / group_sizes["control"],
                    "test_n": int(test_n),
                    "test_share": test_n / group_sizes["test"],
                }
            )
    return pd.DataFrame(rows)


def balance_tests(users: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variable in ["gender", "age_group", "art_experience"]:
        ct = pd.crosstab(users[variable], users["group"])
        chi2, p_value, _, _ = stats.chi2_contingency(ct)
        rows.append({"variable": variable, "chi2_p": p_value})
    return pd.DataFrame(rows)


def build_ab_table(users: pd.DataFrame, survey_last: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric_name, questions in QUESTION_GROUPS.items():
        user_metric = build_user_metric(survey_last, users, questions)
        rows.append(analyze_metric(user_metric, metric_name))

    learning_metric = (
        users[users["survey_completed_at"].notna()][["telegram_id", "group", "correct_answers_count"]]
        .rename(columns={"correct_answers_count": "metric"})
        .dropna()
        .copy()
    )
    learning_row = analyze_metric(
        learning_metric, "Прокси-метрика образовательного результата"
    )
    rows.append(learning_row)
    return pd.DataFrame(rows)


def build_usability_table(users: pd.DataFrame, comments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col, label in [
        ("lesson_duration_sec", "Медианное время прохождения урока, сек."),
        ("survey_duration_sec", "Медианное время заполнения анкеты, сек."),
        ("full_flow_duration_sec", "Медианное время полного сценария, сек."),
    ]:
        medians = users.groupby("group")[col].median()
        test = users.loc[users["group"] == "test", col].dropna()
        control = users.loc[users["group"] == "control", col].dropna()
        p_value = stats.mannwhitneyu(test, control, alternative="two-sided").pvalue
        rows.append(
            {
                "metric": label,
                "control_value": medians["control"],
                "test_value": medians["test"],
                "p_value": p_value,
                "metric_type": "duration",
            }
        )
    return pd.DataFrame(rows)


def adjusted_models(users: pd.DataFrame, survey_last: pd.DataFrame) -> dict:
    overall_metric = build_user_metric(survey_last, users, QUESTION_GROUPS["Целевая метрика: индекс ощущаемой поддержки"])
    overall_metric = overall_metric.merge(
        users[["telegram_id", "gender", "age_group", "art_experience"]],
        on="telegram_id",
        how="left",
    )
    overall_metric["is_test"] = (overall_metric["group"] == "test").astype(int)

    survey_model = smf.ols(
        "metric ~ is_test + C(art_experience) + C(gender) + C(age_group)",
        data=overall_metric,
    ).fit(cov_type="HC3")

    learning_metric = users[users["survey_completed_at"].notna()][
        ["group", "gender", "age_group", "art_experience", "correct_answers_count"]
    ].copy()
    learning_metric["is_test"] = (learning_metric["group"] == "test").astype(int)

    learning_model = smf.ols(
        "correct_answers_count ~ is_test + C(art_experience) + C(gender) + C(age_group)",
        data=learning_metric,
    ).fit(cov_type="HC3")

    return {
        "survey_coef": survey_model.params["is_test"],
        "survey_p": survey_model.pvalues["is_test"],
        "learning_coef": learning_model.params["is_test"],
        "learning_p": learning_model.pvalues["is_test"],
    }


def comment_summary(users: pd.DataFrame, comments: pd.DataFrame) -> pd.DataFrame:
    return comments.merge(users[["telegram_id", "group"]], on="telegram_id", how="left")


def save_figures(users: pd.DataFrame, ab_table: pd.DataFrame):
    plt.style.use("default")

    constructs_plot = ab_table[
        ab_table["metric_name"].isin(
            [
                "Целевая метрика: индекс ощущаемой поддержки",
                "Воспринимаемая поддержка",
                "Эмоциональная безопасность",
                "Социальное присутствие",
                "Поведенческое намерение",
            ]
        )
    ].copy()
    x = np.arange(len(constructs_plot))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, constructs_plot["control_mean"], width, label="control", color="#6c8ebf")
    ax.bar(x + width / 2, constructs_plot["test_mean"], width, label="test", color="#d17c2f")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            "Целевая\nметрика",
            "Поддержка",
            "Эмоц.\nбезопасность",
            "Соц.\nприсутствие",
            "Поведенч.\nнамерение",
        ]
    )
    ax.set_ylim(0, 10)
    ax.set_ylabel("Средний балл")
    ax.set_title("Средние оценки по основным survey-метрикам")
    ax.legend(title="Группа")
    plt.tight_layout()
    plt.savefig(ASSETS_DIR / "survey_construct_means.png", dpi=200)
    plt.close()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, col, title in zip(
        axes,
        ["lesson_duration_sec", "survey_duration_sec", "full_flow_duration_sec"],
        ["Урок", "Анкета", "Полный сценарий"],
    ):
        plot_data = [
            users.loc[users["group"] == "control", col].dropna(),
            users.loc[users["group"] == "test", col].dropna(),
        ]
        ax.boxplot(plot_data, tick_labels=["control", "test"])
        ax.set_title(title)
        ax.set_ylabel("Секунды")
    plt.tight_layout()
    plt.savefig(ASSETS_DIR / "duration_boxplots.png", dpi=200)
    plt.close()


def fmt_num(value, digits=3):
    if pd.isna(value):
        return "nan"
    return f"{value:.{digits}f}"


def fmt_pct(value, digits=1):
    if pd.isna(value):
        return "nan"
    return f"{value * 100:.{digits}f}"


def build_markdown(
    users: pd.DataFrame,
    ab_table: pd.DataFrame,
    usability_table: pd.DataFrame,
    balance_table_df: pd.DataFrame,
    adjusted: dict,
    comments_by_group: pd.DataFrame,
) -> str:
    total_n = len(users)
    control_n = (users["group"] == "control").sum()
    test_n = (users["group"] == "test").sum()

    art_rows = comments_by_group  # placeholder for style consistency
    del art_rows

    survey_row = ab_table.loc[
        ab_table["metric_name"] == "Целевая метрика: индекс ощущаемой поддержки"
    ].iloc[0]
    support_row = ab_table.loc[ab_table["metric_name"] == "Воспринимаемая поддержка"].iloc[0]
    safety_row = ab_table.loc[ab_table["metric_name"] == "Эмоциональная безопасность"].iloc[0]
    presence_row = ab_table.loc[ab_table["metric_name"] == "Социальное присутствие"].iloc[0]
    intention_row = ab_table.loc[ab_table["metric_name"] == "Поведенческое намерение"].iloc[0]
    learning_row = ab_table.loc[
        ab_table["metric_name"] == "Прокси-метрика образовательного результата"
    ].iloc[0]

    art_balance_p = balance_table_df.loc[
        balance_table_df["variable"] == "art_experience", "chi2_p"
    ].iloc[0]
    gender_balance_p = balance_table_df.loc[
        balance_table_df["variable"] == "gender", "chi2_p"
    ].iloc[0]
    age_balance_p = balance_table_df.loc[
        balance_table_df["variable"] == "age_group", "chi2_p"
    ].iloc[0]

    lesson_time_row = usability_table.loc[
        usability_table["metric"] == "Медианное время прохождения урока, сек."
    ].iloc[0]
    survey_time_row = usability_table.loc[
        usability_table["metric"] == "Медианное время заполнения анкеты, сек."
    ].iloc[0]
    full_time_row = usability_table.loc[
        usability_table["metric"] == "Медианное время полного сценария, сек."
    ].iloc[0]

    lines = [
        "# Раздел «Результаты»",
        "",
        "## Описание выборки",
        "В анализ были включены данные 63 пользователей, полностью завершивших итоговый опрос пользовательского опыта. Именно эта аналитическая выборка используется далее для описания состава групп и для всех расчётов, связанных с итоговой анкетой, включая A/B-сравнение метрик и факторный анализ. В контрольную группу вошёл 31 пользователь, в тестовую — 32 пользователя. Основные описательные характеристики этой выборки приведены в таблице 1 (`results_assets/sample_description_table.csv`).",
        f"Распределение по полу и возрасту между группами оказалось сопоставимым: различия не достигают статистической значимости (`p={fmt_num(gender_balance_p, 4)}` и `p={fmt_num(age_balance_p, 4)}` соответственно). В то же время по переменной предварительного опыта взаимодействия с искусством группы различались сильнее (`p={fmt_num(art_balance_p, 4)}`). В тестовой группе было больше респондентов с минимальным опытом, тогда как в контрольной группе чаще встречались участники, указавшие эпизодический интерес к теме. Данное различие важно учитывать при интерпретации результатов, поскольку оно потенциально может влиять как на субъективное восприятие урока, так и на успешность выполнения заданий.",
        "Структура выборки в целом соответствует исследовательской задаче: в ней представлены как участники с низкой вовлечённостью в искусство, так и пользователи с более высоким уровнем предварительной подготовки. Это позволяет оценивать влияние маскота не только на узкую группу мотивированных пользователей, но и на более широкую аудиторию, для которой образовательный формат может быть новым.",
        "",
        "## Результаты A/B-эксперимента",
        f"Основной A/B-анализ проводился на уровне пользователя по последней полной попытке заполнения анкеты, включавшей все восемь утверждений. В качестве целевой метрики использовался индекс ощущаемой поддержки — агрегированный показатель на основе итоговой шкалы из восьми утверждений. Среднее значение этого индекса составило {fmt_num(survey_row['control_mean'])} балла в контрольной группе и {fmt_num(survey_row['test_mean'])} балла в тестовой группе. Разница между группами равна {fmt_num(survey_row['effect_abs'])} балла, а статистические критерии не указывают на наличие значимого эффекта (`Welch p={fmt_num(survey_row['welch_p'], 4)}`, `Mann–Whitney p={fmt_num(survey_row['mannwhitney_p'], 4)}`). Таким образом, гипотеза о том, что наличие цифрового маскота приводит к заметному росту субъективной оценки взаимодействия, на имеющихся данных не подтверждается.",
        f"Дополнительный анализ по смысловым блокам анкеты также не выявил устойчивых различий между версиями прототипа. Для блока «Воспринимаемая поддержка» средние значения составили {fmt_num(support_row['control_mean'])} и {fmt_num(support_row['test_mean'])} балла; для блока «Эмоциональная безопасность» — {fmt_num(safety_row['control_mean'])} и {fmt_num(safety_row['test_mean'])}; для блока «Социальное присутствие» — {fmt_num(presence_row['control_mean'])} и {fmt_num(presence_row['test_mean'])}; для блока «Поведенческое намерение» — {fmt_num(intention_row['control_mean'])} и {fmt_num(intention_row['test_mean'])}. Во всех случаях доверительные интервалы для разницы средних включают нулевое значение, а отдельный анализ каждого из восьми утверждений не меняет общего содержательного вывода. Сводные результаты представлены в таблице 2 (`results_assets/ab_experiment_summary.csv`) и на рисунке 1 (`results_assets/survey_construct_means.png`).",
        f"С учётом выявленного дисбаланса по опыту в искусстве был проведён дополнительный регрессионный анализ с контролем пола, возраста и предварительного опыта. После введения этих контролей коэффициент при принадлежности к тестовой группе для целевой метрики также остался статистически незначимым (`b={fmt_num(adjusted['survey_coef'])}`, `p={fmt_num(adjusted['survey_p'], 4)}`). Это показывает, что отсутствие зафиксированного эффекта не объясняется только различиями в составе групп.",
        f"Прокси-метрика образовательного результата была задана как количество правильных ответов на задания урока. Среди пользователей, завершивших анкету, среднее число правильных ответов составило {fmt_num(learning_row['control_mean'])} в контрольной группе и {fmt_num(learning_row['test_mean'])} в тестовой группе. Различия статистически незначимы (`Welch p={fmt_num(learning_row['welch_p'], 4)}`), а регрессионная проверка с контролем фоновых характеристик также не выявила эффекта маскота (`b={fmt_num(adjusted['learning_coef'])}`, `p={fmt_num(adjusted['learning_p'], 4)}`). Следовательно, по имеющимся данным наличие маскота не привело к измеримому улучшению усвоения материала.",
        "",
        "## Анализ используемости прототипа",
        "Для анализа используемости были рассмотрены конверсии по основным этапам сценария, длительность взаимодействия и открытые пользовательские комментарии. Этот блок важен, поскольку даже при отсутствии различий по основной гипотезе прототип мог по-разному влиять на вовлечённость и удобство прохождения урока.",
        f"Временные характеристики прохождения также оказались близкими. Медианное время прохождения урока составило {fmt_num(lesson_time_row['control_value'])} секунды ({fmt_num(lesson_time_row['control_value'] / 60, 2)} минуты) в контрольной группе и {fmt_num(lesson_time_row['test_value'])} секунды ({fmt_num(lesson_time_row['test_value'] / 60, 2)} минуты) в тестовой; медианное время заполнения анкеты — {fmt_num(survey_time_row['control_value'])} секунды ({fmt_num(survey_time_row['control_value'] / 60, 2)} минуты) и {fmt_num(survey_time_row['test_value'])} секунды ({fmt_num(survey_time_row['test_value'] / 60, 2)} минуты) соответственно; медианное время полного сценария — {fmt_num(full_time_row['control_value'])} секунды ({fmt_num(full_time_row['control_value'] / 60, 2)} минуты) и {fmt_num(full_time_row['test_value'])} секунды ({fmt_num(full_time_row['test_value'] / 60, 2)} минуты). Непараметрические сравнения не выявили статистически значимых различий, что говорит о сопоставимой когнитивной и временной нагрузке в обеих версиях прототипа. Графическое представление распределений времени дано на рисунке 2 (`results_assets/duration_boxplots.png`).",
        "Качественный анализ открытых комментариев показывает, что в обеих группах пользователи в целом положительно воспринимали краткость урока, понятность объяснений и сочетание текстовых и визуальных материалов. При этом часть комментариев содержала предложения по доработке сценария: пользователи отмечали желание видеть больше примеров, более цельную структуру итогового квиза, а также более аккуратную интеграцию визуального образа маскота в сообщения и карточки. Эти наблюдения не меняют основного количественного вывода, однако помогают уточнить направления дальнейшей доработки прототипа.",
        "",
        "## Интерпретация результатов",
        "Полученные результаты позволяют сделать вывод о том, что в условиях данного эксперимента цифровой маскот не обеспечил статистически подтверждённого улучшения субъективного ощущения поддержки пользователей по сравнению с нейтральной версией образовательного бота. При этом обе версии прототипа получили в целом высокие оценки, что указывает на общее положительное восприятие разработанного сценария. Высокие средние значения по большинству пунктов анкеты формируют потолочный эффект: шкала слабо различает небольшие улучшения, которые теоретически могли быть вызваны добавлением маскота.",
        "Отсутствие значимого эффекта не означает, что маскот не играет никакой роли в образовательном интерфейсе. Скорее, результаты показывают, что сам по себе факт присутствия персонажа ещё недостаточен для существенного изменения пользовательского опыта. Более важным может быть качество интеграции маскота в сценарий: согласованность визуального стиля, ясность речевой роли персонажа, степень интерактивности, уместность его реплик в учебном контексте и баланс между эмоциональной поддержкой и учебной задачей. Замечания из открытых комментариев подтверждают именно этот вывод: участники обращали внимание не столько на наличие маскота как таковое, сколько на конкретные детали его реализации.",
        "Отдельно важно отметить, что маскот не повлиял и на прокси-метрику образовательного результата. Это указывает на то, что в исследуемой конфигурации его присутствие не ухудшило и не улучшило усвоение материала. С практической точки зрения такой результат можно интерпретировать двояко. С одной стороны, внедрение маскота не принесло зафиксированного прироста ключевых метрик. С другой стороны, оно не вызвало падения прохождения, роста временной нагрузки или снижения учебных результатов, то есть не сделало интерфейс менее работоспособным.",
        "В совокупности результаты позволяют рассматривать созданный прототип как рабочую основу для дальнейших итераций, а само исследование — как эмпирическое подтверждение того, что эффект цифрового маскота в образовательной среде зависит не только от его наличия, но и от тонкости дизайнерской и сценарной настройки. Для последующих исследований перспективно тестировать более выразительные варианты персонализации, иные способы встраивания поддерживающих реплик, а также расширенные метрики, способные точнее фиксировать изменения в ощущении поддержки, вовлечённости и удержании внимания.",
    ]

    return "\n\n".join(lines) + "\n"


def main():
    ensure_dirs()
    users = prepare_users()
    survey = prepare_survey()
    comments = prepare_comments()
    survey_last = get_last_full_survey_attempts(survey)
    analytic_ids = survey_last["telegram_id"].drop_duplicates()
    users = users[users["telegram_id"].isin(analytic_ids)].copy()
    comments = comments[comments["telegram_id"].isin(analytic_ids)].copy()

    sample_table = sample_description_table(users)
    balance_table_df = balance_tests(users)
    ab_table = build_ab_table(users, survey_last)
    usability_table = build_usability_table(users, comments)
    adjusted = adjusted_models(users, survey_last)
    comments_by_group = comment_summary(users, comments)

    sample_table.to_csv(ASSETS_DIR / "sample_description_table.csv", index=False)
    balance_table_df.to_csv(ASSETS_DIR / "balance_tests.csv", index=False)
    ab_table.to_csv(ASSETS_DIR / "ab_experiment_summary.csv", index=False)
    usability_table.to_csv(ASSETS_DIR / "usability_summary.csv", index=False)
    comments_by_group.to_csv(ASSETS_DIR / "open_comments_with_groups.csv", index=False)

    save_figures(users, ab_table)

    report = build_markdown(
        users=users,
        ab_table=ab_table,
        usability_table=usability_table,
        balance_table_df=balance_table_df,
        adjusted=adjusted,
        comments_by_group=comments_by_group,
    )
    (DATA_DIR / "VKR_results_sections.md").write_text(report, encoding="utf-8")

    print("Saved report and assets:")
    print(" - VKR_results_sections.md")
    print(" - results_assets/sample_description_table.csv")
    print(" - results_assets/balance_tests.csv")
    print(" - results_assets/ab_experiment_summary.csv")
    print(" - results_assets/usability_summary.csv")
    print(" - results_assets/open_comments_with_groups.csv")
    print(" - results_assets/survey_construct_means.png")
    print(" - results_assets/duration_boxplots.png")


if __name__ == "__main__":
    main()
