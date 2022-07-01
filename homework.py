import json
import logging
import os
import requests
import time

from telegram import Bot
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s',
    filename='program.log'
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            logging.error(f'Код ответа не 200: {response.status_code}')
            raise requests.exceptions.RequestException(
                f'Код ответа не 200: {response.status_cod}'
            )
    except requests.exceptions.RequestException as error:
        logging.error(f'Эндпоинт недоступен.Ошибка от сервера: {error}')
        send_message(f'Эндпоинт недоступен. Ошибка от сервера: {error}')
    try:
        return response.json()
    except json.JSONDecodeError:
        logging.error('Сервер вернул невалидный ответ')
        send_message('Сервер вернул невалидный ответ')


def check_response(response):
    """Проверка ответа API на корректность."""
    try:
        homework = response['homeworks']
    except KeyError as error:
        logging.error(f'Ошибка доступа по ключу homeworks: {error}')
    if not isinstance(homework, list):
        logging.error('Homeworks не в виде списка')
        raise TypeError('Homeworks не в виде списка')
    return homework


def parse_status(homework):
    """Извлечение статуса работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logging.error('Неверный ответ сервера')
    homework_status = homework.get('status')
    verdict = ''
    if ((homework_status is None) or (
        homework_status == '')) or ((
            homework_status != 'approved') and (
            homework_status != 'rejected')):
        logging.error(f'Статус работы некорректен: {homework_status}')
        raise KeyError('Homeworks не в виде списка')
    if homework_status == 'rejected':
        verdict = HOMEWORK_STATUSES['rejected']
    elif homework_status == 'approved':
        verdict = HOMEWORK_STATUSES['approved']
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    logging.info('Запущен бот по проверке задания')
    if not check_tokens():
        logging.critical('Не все переменные окружения на месте')
        raise Exception('Не все переменные окружения на месте')
    current_timestamp = 1654402916
    while True:
        try:
            all_homework = get_api_answer(current_timestamp)
            if len(all_homework['homeworks']) > 0:
                homework = check_response(all_homework)[0]
                send_message(bot, parse_status(homework))
                logging.info('Сообщение отправлено')
            time.sleep(RETRY_TIME)

        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            send_message(bot, f'Сбой в работе программы: {error}')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
