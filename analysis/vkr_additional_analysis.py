from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


DATA_DIR = Path(".")
TEST_ACCOUNT_IDS = [426826357, 420252802]
QUESTION_GROUPS = {
    "Perceived support": [1, 2, 7],
    "Emotional safety": [5, 6],
    "Social presence": [3, 4],
    "Behavioral intention": [8],
}


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


def prepare_users(path: Path) -> pd.DataFrame:
    users = pd.read_csv(path)
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

    return users


def prepare_survey(path: Path) -> pd.DataFrame:
    survey = pd.read_csv(path)
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


def prepare_answers(path: Path) -> pd.DataFrame:
    answers = pd.read_csv(path)
    answers.columns = answers.columns.str.strip()
    answers["telegram_id"] = pd.to_numeric(answers["telegram_id"], errors="coerce")
    answers["question_number"] = pd.to_numeric(answers["question_number"], errors="coerce")
    answers["is_correct"] = pd.to_numeric(answers["is_correct"], errors="coerce")
    answers = answers[~answers["telegram_id"].isin(TEST_ACCOUNT_IDS)].copy()
    answers = answers.dropna(subset=["telegram_id", "question_number", "is_correct"]).copy()
    return answers


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

    survey_last = survey.merge(
        last_full_attempts[["telegram_id", "attempt_n"]],
        on=["telegram_id", "attempt_n"],
        how="inner",
    ).copy()

    return survey_last.sort_values(
        ["telegram_id", "answered_at", "survey_question_number"]
    ).copy()


def build_user_metric(
    survey_last: pd.DataFrame,
    users: pd.DataFrame,
    target_questions=None,
    source_col="selected_option",
    question_col="survey_question_number",
):
    metric_source = survey_last.copy()
    if target_questions is not None:
        metric_source = metric_source[metric_source[question_col].isin(target_questions)].copy()

    required_questions = (
        metric_source[question_col].nunique()
        if target_questions is None
        else len(target_questions)
    )
    question_counts = metric_source.groupby("telegram_id")[question_col].nunique()
    complete_users = question_counts[question_counts == required_questions].index
    metric_source = metric_source[metric_source["telegram_id"].isin(complete_users)].copy()

    users_group = users[["telegram_id", "group"]].drop_duplicates(subset=["telegram_id"])

    return (
        metric_source.merge(users_group, on="telegram_id", how="inner")
        .groupby(["telegram_id", "group"], as_index=False)
        .agg(metric=(source_col, "mean"))
    )


def analyze_metric(user_metric: pd.DataFrame, metric_name: str, family: str) -> dict:
    test = user_metric.loc[user_metric["group"] == "test", "metric"].dropna()
    control = user_metric.loc[user_metric["group"] == "control", "metric"].dropna()

    control_mean = control.mean()
    test_mean = test.mean()
    effect_abs = test_mean - control_mean
    effect_pct = effect_abs / control_mean * 100 if control_mean else np.nan
    std_pooled = np.sqrt((test.std() ** 2 + control.std() ** 2) / 2)
    cohens_d = effect_abs / std_pooled if std_pooled else np.nan

    welch = stats.ttest_ind(test, control, equal_var=False)
    mannwhitney = stats.mannwhitneyu(test, control, alternative="two-sided")
    ci_low, ci_high = bootstrap_diff_means(test, control)

    return {
        "family": family,
        "metric_name": metric_name,
        "n_test": len(test),
        "n_control": len(control),
        "control_mean": control_mean,
        "test_mean": test_mean,
        "effect_abs": effect_abs,
        "effect_pct": effect_pct,
        "cohens_d": cohens_d,
        "welch_p": welch.pvalue,
        "mannwhitney_p": mannwhitney.pvalue,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


def add_multiple_testing_correction(results: pd.DataFrame, p_cols) -> pd.DataFrame:
    corrected = results.copy()
    for p_col in p_cols:
        corrected[f"{p_col}_holm"] = multipletests(corrected[p_col], method="holm")[1]
        corrected[f"{p_col}_fdr_bh"] = multipletests(corrected[p_col], method="fdr_bh")[1]
    return corrected


def format_num(value, digits=3):
    if pd.isna(value):
        return "nan"
    return f"{value:.{digits}f}"


def cronbach_alpha(wide_df: pd.DataFrame) -> float:
    n_items = wide_df.shape[1]
    item_var_sum = wide_df.var(axis=0, ddof=1).sum()
    total_var = wide_df.sum(axis=1).var(ddof=1)
    if n_items <= 1 or total_var == 0:
        return np.nan
    return n_items / (n_items - 1) * (1 - item_var_sum / total_var)


def calculate_kmo(corr_matrix: np.ndarray):
    inv_corr = np.linalg.inv(corr_matrix)
    partial_corr = -inv_corr / np.sqrt(np.outer(np.diag(inv_corr), np.diag(inv_corr)))
    np.fill_diagonal(partial_corr, 0)

    corr_no_diag = corr_matrix.copy()
    np.fill_diagonal(corr_no_diag, 0)

    corr_sq_sum = (corr_no_diag**2).sum()
    partial_sq_sum = (partial_corr**2).sum()
    kmo_overall = corr_sq_sum / (corr_sq_sum + partial_sq_sum)

    item_kmo = []
    for i in range(corr_matrix.shape[0]):
        corr_sq_i = np.delete(corr_no_diag[i, :] ** 2, i).sum()
        partial_sq_i = np.delete(partial_corr[i, :] ** 2, i).sum()
        item_kmo.append(corr_sq_i / (corr_sq_i + partial_sq_i))

    return kmo_overall, np.asarray(item_kmo)


def bartlett_sphericity_test(wide_df: pd.DataFrame):
    corr_matrix = wide_df.corr().values
    n = len(wide_df)
    p = corr_matrix.shape[0]
    chi2 = -(n - 1 - (2 * p + 5) / 6) * np.log(np.linalg.det(corr_matrix))
    df = p * (p - 1) / 2
    p_value = 1 - stats.chi2.cdf(chi2, df)
    return chi2, int(df), p_value


def varimax(loadings: np.ndarray, gamma=1.0, q=50, tol=1e-6):
    n_rows, n_cols = loadings.shape
    rotation = np.eye(n_cols)
    d = 0

    for _ in range(q):
        d_old = d
        rotated = loadings @ rotation
        u, s, vh = np.linalg.svd(
            loadings.T
            @ (
                rotated**3
                - (gamma / n_rows) * rotated @ np.diag(np.diag(rotated.T @ rotated))
            )
        )
        rotation = u @ vh
        d = s.sum()
        if d_old != 0 and d / d_old < 1 + tol:
            break

    return loadings @ rotation


def principal_axis_factor_analysis(
    wide_df: pd.DataFrame,
    n_factors: int,
    rotation: str = "varimax",
    max_iter: int = 100,
    tol: float = 1e-6,
):
    corr_matrix = wide_df.corr().values
    inv_corr = np.linalg.inv(corr_matrix)
    communalities = np.clip(1 - 1 / np.diag(inv_corr), 0, 1)

    for _ in range(max_iter):
        reduced = corr_matrix.copy()
        np.fill_diagonal(reduced, communalities)

        eigenvalues, eigenvectors = np.linalg.eigh(reduced)
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[order]
        eigenvectors = eigenvectors[:, order]

        selected_vals = np.clip(eigenvalues[:n_factors], 0, None)
        loadings = eigenvectors[:, :n_factors] * np.sqrt(selected_vals)
        updated_communalities = (loadings**2).sum(axis=1)

        if np.max(np.abs(updated_communalities - communalities)) < tol:
            communalities = updated_communalities
            break

        communalities = updated_communalities

    if rotation == "varimax":
        loadings = varimax(loadings)

    for j in range(loadings.shape[1]):
        strongest_idx = np.argmax(np.abs(loadings[:, j]))
        if loadings[strongest_idx, j] < 0:
            loadings[:, j] *= -1

    ss_loadings = (loadings**2).sum(axis=0)
    prop_var = ss_loadings / wide_df.shape[1]
    cum_var = np.cumsum(prop_var)

    return {
        "loadings": loadings,
        "communalities": communalities,
        "ss_loadings": ss_loadings,
        "prop_var": prop_var,
        "cum_var": cum_var,
    }


def build_factor_wide_table(survey_last: pd.DataFrame) -> pd.DataFrame:
    wide = survey_last.pivot_table(
        index="telegram_id",
        columns="survey_question_number",
        values="selected_option",
        aggfunc="mean",
    ).sort_index(axis=1)
    wide.columns = [f"Q{int(col)}" for col in wide.columns]
    return wide


def exploratory_factor_analysis(survey_last: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = build_factor_wide_table(survey_last)
    corr_matrix = wide.corr()
    eigenvalues = np.linalg.eigvalsh(corr_matrix.values)[::-1]
    n_factors = int((eigenvalues > 1).sum())

    chi2, bartlett_df, bartlett_p = bartlett_sphericity_test(wide)
    kmo_overall, item_kmo = calculate_kmo(corr_matrix.values)
    alpha_total = cronbach_alpha(wide)
    fa_result = principal_axis_factor_analysis(wide, n_factors=n_factors, rotation="varimax")

    question_map = (
        survey_last[["survey_question_number", "question_text"]]
        .drop_duplicates()
        .sort_values("survey_question_number")
    )

    loadings_df = question_map.rename(
        columns={"survey_question_number": "question_number"}
    ).copy()
    for idx in range(n_factors):
        loadings_df[f"factor_{idx + 1}_loading"] = fa_result["loadings"][:, idx]
    loadings_df["communality"] = fa_result["communalities"]
    loadings_df["item_kmo"] = item_kmo
    loadings_df["primary_factor"] = (
        np.abs(fa_result["loadings"]).argmax(axis=1) + 1
    )

    summary_rows = [
        {
            "metric": "n_observations",
            "value": len(wide),
        },
        {
            "metric": "n_items",
            "value": wide.shape[1],
        },
        {
            "metric": "cronbach_alpha_total",
            "value": alpha_total,
        },
        {
            "metric": "kmo_overall",
            "value": kmo_overall,
        },
        {
            "metric": "bartlett_chi2",
            "value": chi2,
        },
        {
            "metric": "bartlett_df",
            "value": bartlett_df,
        },
        {
            "metric": "bartlett_p",
            "value": bartlett_p,
        },
        {
            "metric": "n_factors_kaiser",
            "value": n_factors,
        },
    ]

    for idx, eigenvalue in enumerate(eigenvalues, start=1):
        summary_rows.append(
            {
                "metric": f"eigenvalue_{idx}",
                "value": eigenvalue,
            }
        )

    for idx in range(n_factors):
        summary_rows.extend(
            [
                {
                    "metric": f"factor_{idx + 1}_ss_loadings",
                    "value": fa_result["ss_loadings"][idx],
                },
                {
                    "metric": f"factor_{idx + 1}_prop_var",
                    "value": fa_result["prop_var"][idx],
                },
                {
                    "metric": f"factor_{idx + 1}_cum_var",
                    "value": fa_result["cum_var"][idx],
                },
            ]
        )

    return pd.DataFrame(summary_rows), loadings_df


def build_markdown_summary(
    construct_results: pd.DataFrame,
    question_results: pd.DataFrame,
    learning_results: pd.DataFrame,
    factor_summary: pd.DataFrame,
    factor_loadings: pd.DataFrame,
) -> str:
    q8_row = question_results.loc[question_results["question_number"] == 8].iloc[0]
    q8_mw_holm = q8_row["mannwhitney_p_holm"]
    kmo = factor_summary.loc[factor_summary["metric"] == "kmo_overall", "value"].iloc[0]
    bartlett_p = factor_summary.loc[factor_summary["metric"] == "bartlett_p", "value"].iloc[0]
    alpha_total = factor_summary.loc[
        factor_summary["metric"] == "cronbach_alpha_total", "value"
    ].iloc[0]
    n_factors = int(
        factor_summary.loc[factor_summary["metric"] == "n_factors_kaiser", "value"].iloc[0]
    )
    factor1_var = factor_summary.loc[
        factor_summary["metric"] == "factor_1_prop_var", "value"
    ].iloc[0]
    factor2_var = factor_summary.loc[
        factor_summary["metric"] == "factor_2_prop_var", "value"
    ].iloc[0]
    factor2_qs = factor_loadings.loc[
        factor_loadings["primary_factor"] == 2, "question_number"
    ].tolist()

    lines = [
        "# Дополнение к анализу VKR_results",
        "",
        "## Что добавлено",
        "- сравнение по смысловым группам утверждений со слайда 7 предзащиты;",
        "- сравнение по каждому из 8 утверждений отдельно;",
        "- сравнение результатов тестирования как прокси-метрики образовательного результата;",
        "- поправка на множественные проверки для анализа по отдельным утверждениям;",
        "- exploratory factor analysis структуры анкеты.",
        "",
        "## Краткий вывод",
        "- По смысловым группам (`Perceived support`, `Emotional safety`, `Social presence`) статистически значимых различий между `test` и `control` не обнаружено.",
        f"- На уровне отдельных утверждений только вопрос `Q8` показывает номинально значимое снижение в `test`: среднее {format_num(q8_row['test_mean'])} против {format_num(q8_row['control_mean'])}, разница {format_num(q8_row['effect_abs'])}, Mann-Whitney p={format_num(q8_row['mannwhitney_p'], 4)}.",
        f"- После поправки Holm на 8 отдельных проверок эффект по `Q8` уже не достигает порога 0.05: p_adj={format_num(q8_mw_holm, 4)}. Поэтому корректнее трактовать его как исследовательский сигнал, а не как устойчиво подтверждённый эффект.",
        f"- Факторный анализ можно использовать как дополнительную проверку структуры анкеты: `KMO={format_num(kmo, 3)}`, тест Бартлетта значим (`p<{format_num(max(bartlett_p, 1e-10), 10)}`), общая согласованность шкалы высокая (`alpha={format_num(alpha_total, 3)}`).",
        f"- По критерию Кайзера выделяются {n_factors} фактора, которые объясняют около {format_num((factor1_var + factor2_var) * 100, 1)}% общей дисперсии. Первый фактор имеет характер общей позитивной оценки взаимодействия, второй в большей степени связан с вопросами {factor2_qs} о дружелюбии и отсутствии страха ошибиться.",
    ]

    learning_row = learning_results.loc[
        learning_results["metric_name"] == "Survey completers only"
    ].iloc[0]
    lines.extend(
        [
            f"- По прокси-метрике образовательного результата (`correct_answers_count`) статистически значимых различий нет: среди завершивших анкету среднее {format_num(learning_row['test_mean'])} в `test` против {format_num(learning_row['control_mean'])} в `control`, Welch p={format_num(learning_row['welch_p'], 4)}.",
            "- Это означает, что по имеющимся данным маскот не показал заметного влияния на усвоение материала.",
            "",
            "## Файлы",
            "- `ab_test_results_by_construct.csv`",
            "- `ab_test_results_by_question.csv`",
            "- `learning_outcome_results.csv`",
            "- `lesson_question_results.csv`",
            "- `factor_analysis_summary.csv`",
            "- `factor_analysis_loadings.csv`",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    users = prepare_users(DATA_DIR / "users_2.csv")
    survey = prepare_survey(DATA_DIR / "survey_answers_2.csv")
    answers = prepare_answers(DATA_DIR / "answers_2.csv")
    survey_last = get_last_full_survey_attempts(survey)

    question_map = (
        survey_last[["survey_question_number", "question_text"]]
        .drop_duplicates()
        .sort_values("survey_question_number")
        .rename(columns={"survey_question_number": "question_number"})
    )

    construct_rows = []
    for construct_name, questions in QUESTION_GROUPS.items():
        user_metric = build_user_metric(survey_last, users, target_questions=questions)
        construct_rows.append(
            {
                **analyze_metric(user_metric, construct_name, family="construct"),
                "questions": ",".join(map(str, questions)),
            }
        )

    construct_results = pd.DataFrame(construct_rows)

    question_rows = []
    for question_number in range(1, 9):
        user_metric = build_user_metric(survey_last, users, target_questions=[question_number])
        question_text = question_map.loc[
            question_map["question_number"] == question_number, "question_text"
        ].iloc[0]
        question_rows.append(
            {
                **analyze_metric(user_metric, f"Q{question_number}", family="question"),
                "question_number": question_number,
                "question_text": question_text,
            }
        )

    question_results = add_multiple_testing_correction(
        pd.DataFrame(question_rows),
        p_cols=["welch_p", "mannwhitney_p"],
    )

    learning_rows = []
    learning_samples = {
        "All registered users": users,
        "Lesson completers only": users[users["lesson_completed_at"].notna()].copy(),
        "Survey completers only": users[users["survey_completed_at"].notna()].copy(),
    }
    for metric_name, subset in learning_samples.items():
        user_metric = (
            subset[["telegram_id", "group", "correct_answers_count"]]
            .rename(columns={"correct_answers_count": "metric"})
            .dropna()
            .copy()
        )
        learning_rows.append(analyze_metric(user_metric, metric_name, family="learning"))

    learning_results = pd.DataFrame(learning_rows)

    factor_summary, factor_loadings = exploratory_factor_analysis(survey_last)

    lesson_question_rows = []
    for question_number, subset in answers.groupby("question_number"):
        question_text = subset["question_text"].dropna().iloc[0]
        user_metric = build_user_metric(
            subset.rename(columns={"question_number": "survey_question_number"}),
            users,
            target_questions=[question_number],
            source_col="is_correct",
            question_col="survey_question_number",
        )
        lesson_question_rows.append(
            {
                **analyze_metric(
                    user_metric, f"Lesson Q{int(question_number)}", family="lesson_question"
                ),
                "question_number": int(question_number),
                "question_text": question_text,
            }
        )

    lesson_question_results = add_multiple_testing_correction(
        pd.DataFrame(lesson_question_rows),
        p_cols=["welch_p", "mannwhitney_p"],
    )

    construct_results.to_csv(DATA_DIR / "ab_test_results_by_construct.csv", index=False)
    question_results.to_csv(DATA_DIR / "ab_test_results_by_question.csv", index=False)
    learning_results.to_csv(DATA_DIR / "learning_outcome_results.csv", index=False)
    lesson_question_results.to_csv(DATA_DIR / "lesson_question_results.csv", index=False)
    factor_summary.to_csv(DATA_DIR / "factor_analysis_summary.csv", index=False)
    factor_loadings.to_csv(DATA_DIR / "factor_analysis_loadings.csv", index=False)

    summary = build_markdown_summary(
        construct_results=construct_results,
        question_results=question_results,
        learning_results=learning_results,
        factor_summary=factor_summary,
        factor_loadings=factor_loadings,
    )
    (DATA_DIR / "VKR_results_addendum.md").write_text(summary, encoding="utf-8")

    print("Saved:")
    print(" - ab_test_results_by_construct.csv")
    print(" - ab_test_results_by_question.csv")
    print(" - learning_outcome_results.csv")
    print(" - lesson_question_results.csv")
    print(" - factor_analysis_summary.csv")
    print(" - factor_analysis_loadings.csv")
    print(" - VKR_results_addendum.md")


if __name__ == "__main__":
    main()
