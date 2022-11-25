import os
import time
from logging import StreamHandler
from pprint import pprint

import requests
import logging


from telegram import Bot
from telegram.ext import CommandHandler, Updater
from dotenv import load_dotenv

from exceptions import TokenException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {TOKENS.get("PRACTICUM_TOKEN")}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> None:
    load_dotenv()
    for token in TOKENS:
        if TOKENS[token] is None:
            return False
            # logger.critical('Нет переменных окружения, работа невозможна')
            # raise TokenException(f'{token} не доступен')


bot = Bot(token=TOKENS.get('TELEGRAM_TOKEN'))


def send_message(bot: Bot, message: str) -> None:
    chat_id = TOKENS.get('TELEGRAM_CHAT_ID')
    bot.send_message(chat_id, message)


def get_api_answer(timestamp: int) -> dict:
    return requests.get(ENDPOINT, headers=HEADERS,
                        params={'from_date': timestamp}).json()


# pprint(get_api_answer(1666544244))


def check_response(response: dict) -> bool:
    return all([
        type(response.get('homeworks')) is list,
        type(response.get('current_date')) is int,
    ])


# pprint(check_response(get_api_answer(1666544244)))


def parse_status(homework: dict) -> str:
    return f'Изменился статус проверки работы "{homework.get("homework_name")}". {HOMEWORK_VERDICTS.get(homework.get("status"))}'


def main() -> None:
    """Основная логика работы бота."""
    timestamp = 0
    check_tokens()
    check_response(get_api_answer(timestamp))
    bot = Bot(TELEGRAM_TOKEN)
    id1, id2 = 0, get_api_answer(timestamp).get('homeworks')[0].get('id')
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )
    logger = logging.getLogger(__name__)
    logger.addHandler(StreamHandler())

    # logger.debug('Сообщение в Telegram отправлено')
    #
    # logger.warning('Большая нагрузка!')
    # logger.error('сбой при отправке сообщения в Telegram')
    # logger.critical('Нет переменных окружения, работа невозможна')

    while True:
        check_tokens()
        check_response(get_api_answer(timestamp))
        try:
            homework = get_api_answer(timestamp).get('homeworks')[0]
            if id2 - id1 != 0:
                send_message(bot, parse_status(homework))
                logger.debug('Сообщение в Telegram отправлено')
            time.sleep(RETRY_PERIOD)
            id1, id2 = id2, get_api_answer(timestamp).get('homeworks')[0].get('id')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)




    # # А тут установлены настройки логгера для текущего файла - example_for_log.py
    # logger = logging.getLogger(__name__)
    # # Устанавливаем уровень, с которого логи будут сохраняться в файл
    # logger.setLevel(logging.INFO)
    # # Указываем обработчик логов
    # handler = RotatingFileHandler('../kittybot/my_logger.log',
    #                               maxBytes=50000000, backupCount=5,
    #                               encoding='utf8')
    # logger.addHandler(handler)
    # formatter = logging.Formatter(
    #     '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    # )
    #
    # # Применяем его к хэндлеру
    # handler.setFormatter(formatter)
    #
    # logger.debug('123')
    # logger.info('Сообщение отправлено')
    # logger.warning('Большая нагрузка!')
    # logger.error('Бот не смог отправить сообщение')
    # logger.critical('Всё упало! Зовите админа!1!111')


if __name__ == '__main__':
    main()
