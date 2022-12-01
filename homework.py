import logging
import os
import time
from http import HTTPStatus
from logging import StreamHandler
from typing import Union

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HTTPError, SendMessageError, StatusError, TokenError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600  # 10 minutes, 60*10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

MESSAGE_ERROR_CURRENT_DATE_KEY = (
    'по ключу `{current_date}` возвращается не тип данных "int"'
)
MESSAGE_ERROR_DICT = 'Отклик не является словарем'
MESSAGE_ERROR_HOMEWORKS_KEY = 'По ключу `{homeworks}` передается не список'
MESSAGE_ERROR_HOMEWORKS_NONE = 'Ключ `{homework_name}` не обнаружен'
MESSAGE_ERROR_REQUEST = 'Ошибка запроса'

MESSAGE_TELEGRAM = 'Сообщение в телеграмм отправлено'

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(funcName)s',
)
logger = logging.getLogger(__name__)
logger.addHandler(StreamHandler())


def check_tokens() -> None:
    """Доступность токенов в переменных окружения.

    Raises:
        TokenError: отстутствует какой либо из необходимых токенов.
    """
    notoken = [
        token
        for token in ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
        if globals().get(token) is None
    ]
    if notoken:
        logger.critical('Необходимый токен: %s не обнаружен', notoken)
        raise TokenError(notoken)


def send_message(bot: telegram.Bot, message: Union[str, Exception]) -> None:
    """
    Отправляет сообщения в телеграм.

    Args:
        bot: объект телеграм бота
        message: передаваемое сообщение или ошибка

    Raises:
        SendMessageError: Если ошибка отправки сообщения через телеграм
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as err:
        logging.exception('Сообщение не отправлено')
        raise SendMessageError from err
    logger.debug(MESSAGE_TELEGRAM)


def get_api_answer(timestamp: int) -> dict:
    """Получаем ответ от эндпоинта.

    Args:
        timestamp: Текущее время в unix формате.

    Returns:
        Резульаты опроса API.

    Raises:
        HTTPError: Ошибка доступа к эндпоинту.
    """
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
    except requests.RequestException as err:
        logging.exception(MESSAGE_ERROR_REQUEST)
        raise HTTPError from err

    if response.status_code != HTTPStatus.OK:
        logger.error(MESSAGE_ERROR_REQUEST)
        raise HTTPError
    return response.json()


def check_response(response: dict) -> dict:
    """Проверка ответа эндпоинта на соответствие документации API.

    Args:
        response: Проверяемый словарь.

    Returns:
        Проверенный словарь.

    Raises:
        TypeError: Ошибка несоответствия типа данных ожидаемому.
    """
    if not isinstance(response, dict):
        logger.error(MESSAGE_ERROR_DICT)
        raise TypeError(MESSAGE_ERROR_DICT)

    if not isinstance(response.get('current_date'), int):
        logger.error(MESSAGE_ERROR_CURRENT_DATE_KEY)
        raise TypeError(MESSAGE_ERROR_CURRENT_DATE_KEY)

    if not isinstance(response.get('homeworks'), list):
        logger.error(MESSAGE_ERROR_HOMEWORKS_KEY)
        raise TypeError(MESSAGE_ERROR_HOMEWORKS_KEY)
    return response


def parse_status(homework: dict) -> str:
    """Получение строки для отправки телеграм.

    Args:
        homework: Сведения о домашней работе.

    Returns:
        Отформатированная строка для отправки в телеграм.

    Raises:
        StatusError: Несоответствие статуса домашней работы ожидаемому.
        NameError: Отсутствие ключа `{homework_name}` в словаре `{homework}`.
    """
    status = homework.get('status')

    if status not in HOMEWORK_VERDICTS or status is None:
        logger.error('Неожиданный статус домашней работы: %s', status)
        raise StatusError
    if homework.get('homework_name') is None:
        logger.error(MESSAGE_ERROR_HOMEWORKS_NONE)
        raise NameError(MESSAGE_ERROR_HOMEWORKS_NONE)
    return (
        'Изменился статус проверки работы '
        f'"{homework.get("homework_name")}". '
        f'{HOMEWORK_VERDICTS.get(homework.get("status"))}'
    )


def main() -> None:
    """Основная логика работы бота."""
    check_tokens()
    timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    error = ''

    while True:
        try:
            response = check_response(get_api_answer(timestamp)).get('homeworks')
            if response:
                status_message = parse_status(response[0])
                send_message(bot, status_message)
            else:
                logger.debug('Статус не обновлялся')
        except (TypeError, HTTPError, StatusError, NameError) as err:
            if err != error:
                send_message(bot, err)
                error = err
        except Exception as err:
            logging.exception('Неизвестная ошибка')
            if err != error:
                send_message(bot, err)
                error = err
        else:
            timestamp = get_api_answer(timestamp).get('current_date')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
