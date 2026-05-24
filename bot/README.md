# Telegram A/B bot

## Запуск

1. Установить зависимости:
   `pip install -r requirements.txt`
2. Заполнить `.env`
3. Запустить:
   `python main.py`

## Структура

- `main.py` – запуск бота
- `config.py` – чтение `.env`
- `db.py` – SQLite и запись событий
- `ab_logic.py` – распределение по группам
- `handlers.py` – onboarding, урок, тест, опрос
- `keyboards.py` – inline-кнопки
- `states.py` – FSM состояния
- `analytics.py` – базовые метрики для A/B анализа
