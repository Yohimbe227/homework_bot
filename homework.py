import logging
import os
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
from dotenv import load_dotenv
import telegram

from exceptions import TokenException, HTTPError, StatusError, SendMessageError

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

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s, %(levelname)s, %(message)s, %(name)s",
)
logger = logging.getLogger(__name__)
logger.addHandler(StreamHandler())


def check_tokens() -> bool:
    """Доступность токенов в переменных окружения."""
    for token in [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]:
        if token is None:
            raise TokenException('Токен не доступен')
        return True


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено')
    except Exception:
        logger.error('Ошибка отправки сообщения')
        raise SendMessageError('Ошибка отправки сообщения')


def get_api_answer(timestamp: int) -> dict:
    """Получаем ответ от эндпоинта."""
    try:
        request = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        if request.status_code != HTTPStatus.OK:
            raise HTTPError('Эндпоинт не доступен')
        return request.json()
    except requests.RequestException:
        raise HTTPError('Эндпоинт не доступен')


def check_response(response: dict) -> None:
    """Проверка ответа эндпоинта на соответствие документации API."""
    if not isinstance(response, dict) or not isinstance(
            response.get('current_date'), int) or not isinstance(
        response.get('homeworks'), list):
        raise TypeError('Структура данных API не соответствует ожиданиям')
    if response.get('homeworks') is None:
        raise NameError('Ключ homework_name не обнаружен')


def parse_status(homework: dict) -> str:
    """Получение строки для отправки телеграм."""
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS or status is None:
        raise StatusError('неожиданный статус домашней работы')
    if homework.get('homework_name') is None:
        raise NameError('Ключ homework_name не обнаружен')

    return ('Изменился статус проверки работы '
            f'"{homework.get("homework_name")}". '
            f'{HOMEWORK_VERDICTS.get(homework.get("status"))}')


def main() -> None:
    """Основная логика работы бота."""

    try:
        check_tokens()
    except TokenException as error:
        logger.critical(error, exc_info=True)
        raise error

    timestamp = 1663660860
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    status1 = ''
    status2 = get_api_answer(timestamp).get('homeworks')[0].get(
        'status') if len(
        get_api_answer(timestamp).get('homeworks')) > 0 else ''

    count1, count2, count3 = 0, 0, 0
    while True:
        try:
            check_response(get_api_answer(timestamp))
        except TypeError:
            logger.error('Структура данных API не соответствует ожиданиям')
            if count1 == 0:
                send_message(bot,
                             'Структура данных API не соответствует ожиданиям')
        except NameError:
            logger.error('Ключ homework_name не обнаружен')
            if count2 == 0:
                send_message(bot, 'Ключ homework_name не обнаружен')
                count2 += 1
        except requests.RequestException:
            logger.error('ошибка RequestException', exc_info=True)
            if count3 == 0:
                send_message(bot, 'ошибка RequestException')
                count3 += 1

        if status1 != status2:
            try:
                send_message(
                    bot,
                    parse_status(
                        get_api_answer(timestamp).get("homeworks")[0]
                    ),
                )
                logger.debug('cообщение в Telegram отправлено')
            except SendMessageError:
                logger.error('ошибка SendMessageError', exc_info=True)
        else:
            logger.debug('отсутствие в ответе новых статусов')
        time.sleep(RETRY_PERIOD)
        status1, status2 = status2, get_api_answer(timestamp).get(
            'homeworks'
        )[0].get('status')


if __name__ == '__main__':
    main()
