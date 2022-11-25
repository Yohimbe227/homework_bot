import logging
import os
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

from exceptions import TokenException

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens() -> bool:
    """Доступность токенов в переменных окружения."""
    for token in [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]:
        if token is None:
            return False
        return True


def send_message(bot: Bot, message: str) -> None:
    """Отправка сообщения в телеграм."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(timestamp: int) -> dict:
    """Получаем ответ от эндпоинта."""

    return requests.get(
        ENDPOINT, headers=HEADERS, params={"from_date": timestamp}
    ).json()


def check_response(response: dict) -> bool:
    """Проверка ответа эндпоинта на соответствие документации API."""
    return all(
        [
            type(response.get("homeworks")) is list,
            type(response.get("current_date")) is int,
        ]
    )


def parse_status(homework: dict) -> str:
    """Получение строки для отправки телеграм."""
    return (f'Изменился статус проверки работы '
            f'"{homework.get("homework_name")}". '
            f'{HOMEWORK_VERDICTS.get(homework.get("status"))}')


def main() -> None:
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s, %(levelname)s, %(message)s, %(name)s",
    )
    logger = logging.getLogger(__name__)
    logger.addHandler(StreamHandler())
    if not check_tokens():
        logger.critical("Нет переменных окружения, работа невозможна")
        raise TokenException(f"Нет переменных окружения, работа невозможна")
    timestamp = 1663660860
    bot = Bot(TELEGRAM_TOKEN)
    status1, status2 = 0, get_api_answer(timestamp).get("homeworks")[0].get(
        "status"
    )

    count1, count2, count3 = 0, 0, 0
    while True:
        try:
            if requests.get(ENDPOINT).status_code == HTTPStatus.NOT_FOUND:
                count1 += 1
                logger.error("эндпоинт яндекса не доступен")
                if count1 == 1:
                    send_message(bot, "эндпоинт яндекса не доступен")
            if not check_response(get_api_answer(timestamp)):
                count2 += 1
                logger.error("отсутствуют ожидаемые ключи в ответе API")
                if count2 == 1:
                    send_message(
                        bot, "отсутствуют ожидаемые ключи в ответе API"
                    )
            if (
                get_api_answer(timestamp).get("homeworks")[0].get("status")
                not in HOMEWORK_VERDICTS
            ):
                count3 += 1
                logger.error("неожиданный статус домашней работы")
                if count3 == 1:
                    send_message(bot, "неожиданный статус домашней работы")
            if status1 != status2:
                send_message(
                    bot,
                    parse_status(
                        get_api_answer(timestamp).get("homeworks")[0]
                    ),
                )
                logger.debug("cообщение в Telegram отправлено")
            else:
                logger.debug("отсутствие в ответе новых статусов")
            time.sleep(RETRY_PERIOD)
            status1, status2 = status2, get_api_answer(timestamp).get(
                "homeworks"
            )[0].get("id")
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error("Неопределенный сбой в работе программы")
            send_message(bot, message)


if __name__ == "__main__":
    main()
