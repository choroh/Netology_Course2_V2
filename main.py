"""
Netology. Курсовая работа.
Используя данные из VK, нужно сделать сервис намного лучше, чем Tinder, а именно: чат-бота "VKinder".
Бот должен искать людей, подходящих под условия, на основании информации о пользователе из VK:

    возраст,
    пол,
    город,
    семейное положение.

У тех людей, которые подошли по требованиям пользователю, получать топ-3 популярных фотографии профиля и
отправлять их пользователю в чат вместе со ссылкой на найденного человека.
Популярность определяется по количеству лайков и комментариев.

Входные данные

Имя пользователя или его id в ВК, для которого мы ищем пару.

    если информации недостаточно нужно дополнительно спросить её у пользователя.

Требование к сервису:

    1. Код программы удовлетворяетPEP8.
    2. 0Получать токен от пользователя с нужными правами.
    3. Программа декомпозирована на функции/классы/модули/пакеты.
    4.Результат программы записывать в БД.
    5. Люди не должны повторяться при повторном поиске.
    6. Не запрещается использовать внешние библиотеки для vk.

01.11.21
"""

import json
from random import randrange

import vk_my_package.vk_find_user_modul
import vk_my_package.api_vk
import db.db
import re

vk_client = vk_my_package.vk_find_user_modul.VKUser()
list_info_for_db = []  # Список словарей с данными для записи в БД

with open('files/config.txt', 'r', encoding='UTF-8') as f:
    my_token = f.readline().strip()


def get_photo(i: int) -> dict:
    """
    Функция получает список найденных кандидатов, id пользователя
    Заносит данные о кандидате в базу данных
    :param list_find:
    :param vk_client:
    :param owner_id:
    :return:
    """
    if vk_client.get_photos(i):  # Если получили id подходящего кандидата с фото
        account = 'https://vk.com/id' + str(i)
        dict_photo = vk_client.get_photos(i)
        list_photo = vk_client.photo_info(dict_photo)

        if list_photo:
            kandidat_photo = {'url_account': account, 'url_photo1': list_photo[0].get('id_photo'),
                              'url_photo2': list_photo[1].get('id_photo'), 'url_photo3': list_photo[2].get('id_photo')}
            return kandidat_photo


def check_user_params(owner_id_: int, owner_params_: dict) -> dict:
    """
    Функция проверяет на наличие необходимых данных у пльзователя.
    Если не хватает - запрашивает и добавляте в словарь данных пользователя
    :param owner_id_:
    :param owner_params_:
    :return:
    """
    owner_params = owner_params_
    owner_id = owner_id_
    if not owner_params.get('city', None):  # Если не указан город
        vk_my_package.api_vk.write_msg(owner_id, 'Укажите ваш город')
        city = vk_my_package.api_vk.dialog()[1].title()
        owner_params['city'] = city

    if owner_params.get('sex') not in (1, 2):  # Если не указан пол
        message = """
        Укажите ваш пол
        женщина - 1
        мужчина - 2
        """
        vk_my_package.api_vk.write_msg(owner_id, message)
        sex = vk_my_package.api_vk.dialog()[1]
        owner_params[sex] = sex

    if not owner_params.get('bdate', None) or not re.findall('\d{1,2}.\d{1,2}.\d{4}', owner_params.get('bdate')):
        # Если не указан год или неверный формат
        vk_my_package.api_vk.write_msg(owner_id, 'Укажите ваш год рождения "дд.мм.гггг')
        bdate = vk_my_package.api_vk.dialog()[1]
        owner_params['bdate'] = bdate
    return owner_params


def send_message_to_user(owner_id, kandidat_id):
    """
    Функция принимает словарь с данными пользователя, id пользователя
    Отеравляет пользователю результат поиска
    """
    kandidat_info = vk_client.get_user(kandidat_id)
    # print('kandidat_info', kandidat_info)
    kandidat_photo = get_photo(kandidat_id)
    if kandidat_photo and kandidat_info:
        vk_my_package.api_vk.write_msg(owner_id, 'Подходящие кандидаты: ')
        if kandidat_photo:  # Если найден кандидат подходящий по всем параметрам с фото
            vk_my_package.api_vk.write_msg(owner_id, 'Аккаунт кандидата: ')
            vk_my_package.api_vk.write_msg(owner_id,
                                           f"{kandidat_info[0].get('first_name')} {kandidat_info[0].get('last_name')} {kandidat_photo.get('url_account')}")
            vk_my_package.api_vk.write_msg(owner_id, 'Фотография кандидата 1:',
                                           f"photo{kandidat_id}_{kandidat_photo.get('url_photo1')}")
            vk_my_package.api_vk.write_msg(owner_id, 'Фотография кандидата 2:',
                                           f"photo{kandidat_id}_{kandidat_photo.get('url_photo2')}")
            vk_my_package.api_vk.write_msg(owner_id, 'Фотография кандидата 3:',
                                           f"photo{kandidat_id}_{kandidat_photo.get('url_photo3')}")
            vk_my_package.api_vk.write_msg(owner_id, '*' * 40)


def send_to_db(owner_id: int, find:bool,  **kandidat: dict) -> bool:
    """
    Функция проверяет пользователя на наличие в БД и если его нет заносит id пользователя в таблицу vk_users базы данных.
    Данные кандидата в таблицу vk_kandidat
    В промежуточную таблицу insert_vk_users_vk_kandidat(*id_user, *id_kandidat)
    """
    kandidat_id = kandidat.get('id')
    try:
        user_inlist = db.db.if_user_inlist(owner_id)
        #  Проверяем на наличие текущего id пользователя в БД. Если нет - заносим
        if not user_inlist:
            db.db.insert_user(owner_id)
    except Exception as Error:
        print('База данных временно недоступна. owner_id не внесен в БД', {Error})

    try:
        kandidat_id_for_user_id = db.db.get_kandidat_id_for_user_id(owner_id, kandidat_id)
        if not kandidat_id_for_user_id:
            # Если текущего кандидата нет в списке просмотренных данным пользователем
            if not kandidat.get('is_closed'):
                #  Если текущий кандидат не заблокирован
                db.db.insert_kandidat(owner_id, kandidat)  # Занесли в БД информацию о кандидате
                find = True
    except Exception as Error:
        print('База данных временно недоступна, возможны повторы', {Error})
        vk_my_package.api_vk.write_msg(owner_id, 'База данных временно недоступна, возможны повторы.')
    return find


def dialog() -> int:
    """
    Функция получает текст от пользователя VK и обрабатывает его.
    Если пользователь наберет "поиск пары" запускается программа поиска пары.
    Выдает id пользователя
    """
    user_message = vk_my_package.api_vk.dialog()
    owner_id = user_message[0]
    owner_message = user_message[1]

    bot_message = f"""
            Вы зашли в службу поиска пары среди пользователей VK
            Для поиска пары, напишите 'поиск пары'"""
    vk_my_package.api_vk.write_msg(owner_id, bot_message)

    while owner_message != 'поиск пары':  # Ждем от пользователя фразы поиска

        if 'привет' in owner_message:
            bot_message = 'Приветствую пользователя службы поиска пары на VK!'
            vk_my_package.api_vk.write_msg(owner_id, bot_message)

        elif 'что ты можешь' in owner_message:
            bot_message = f"""Я могу найти среди пользователей VK подходящую для вас пару\n
                Для поиска пары, напишите 'поиск пары'"""
            vk_my_package.api_vk.write_msg(owner_id, bot_message)

        elif 'ты кто' in owner_message or 'кто ты' in owner_message:
            bot_message = f"""Я бот. Я могу найти среди пользователей VK подходящую для вас пару\n
                Для поиска пары, напишите 'поиск пары'"""
            vk_my_package.api_vk.write_msg(owner_id, bot_message)

        elif any(('не нашел' in owner_message, 'не найден' in owner_message, 'не обнаруженно' in owner_message)):
            bot_message = f"""Возможно в данный момент подходящей кандидатуры нет. 
            Попробуйте повторитьпоиск в другой раз."""
            vk_my_package.api_vk.write_msg(owner_id, bot_message)

        elif 'пока' in owner_message:
            bot_message = 'Удачи! Заходите еще.'
            vk_my_package.api_vk.write_msg(owner_id, bot_message)

        else:
            bot_message = 'Для поиска пары, напишите "поиск пары"'
            vk_my_package.api_vk.write_msg(owner_id, bot_message)

        owner_message = ''
        owner_message = vk_my_package.api_vk.dialog()[1]
    return owner_id


def search_by_status(owner_id: int, **owner_params: dict) -> list:
    """
    Функция запускает механизм поиска кандидатоа для различных статусов.
    Выдает список найденных кандидатов
    """
    kandidats = []
    vk_my_package.api_vk.write_msg(owner_id, 'Идет поиск кандидатов')
    temp = vk_client.user_search(owner_params, 1)  # холост
    if temp:
        kandidats += (temp.get('items'))

    temp = vk_client.user_search(owner_params, 6)  # в активном поиске
    if temp:
        kandidats += (temp.get('items'))

    temp = vk_client.user_search(owner_params, 0)  # не указано
    if temp:
        kandidats += (temp.get('items'))
    return kandidats

def main():
    """
    При получении от пользователя группы сообщения "Поиск пары", из текста получаем id пользователя vk
    По его id получаем необходимые данные для выяснения требований поиска.
    Если у пользователя в аккаунте не достаточно данных - запрашиваем в сообщении.
    Сканируем пользователей vk, отбираем удовлетворяющих требованиям.
    Информация о найденных кандидатах для данного пользователя заносится в базу данных и отправляется пользователю в сообщении.
    :return:
    """
    owner_id = dialog()  # Получаем от пользователя из его сообщения его id
    owner_info = vk_client.get_user(owner_id)  # Получили в списке словарь с необходимыми данными пользователя
    owner_params = vk_client.user_info(owner_info)  # Сформировали нужные данные
    #owner_params = {'bdate': '01.01.1988', 'sex': 2, 'city': 'Москва', 'relation': 1}
    # Параметры пользователя для тестирования
    print('owner_info', owner_info)
    print('owner_params', owner_params)

    print()
    kandidats = search_by_status(owner_id, **owner_params)  # Получаем список кандидатов при различных статусах

    for i in kandidats:
        if get_photo(i.get('id')):
            kandidat_id = i.get('id')
            photo_info = get_photo(kandidat_id)
            kandidat_info_full = {**i, **photo_info}
            list_info_for_db.append(kandidat_info_full)
            print('kandidat_info_full', kandidat_info_full)
            try:
                kandidat_id_for_user_id = db.db.get_kandidat_id_for_user_id(owner_id, kandidat_id)
                if (not kandidat_id_for_user_id):
                    # Если текущего кандидата нет в списке просмотренных данным пользователем
                    send_message_to_user(owner_id, kandidat_id)
            except Exception as Error:
                print('База данных временно недоступна, возможны повторы', {Error})
                vk_my_package.api_vk.write_msg(owner_id, 'База данных временно недоступна, возможны повторы.')
                send_message_to_user(owner_id, kandidat_id)
    print('list_info_for_db', list_info_for_db)

    #  Ищем кандидатов для данного пользователя
    if list_info_for_db:
        find = False
        #  Отправляем результаты поиска пользователю в сообщении
        for kandidat in list_info_for_db:
            find = send_to_db(owner_id, find, **kandidat)
        list_info_for_db.clear()

    if not find:
        print('Новых записей удовлетворяющих запросу не обнаруеженно.')
        vk_my_package.api_vk.write_msg(owner_id, 'Новых записей удовлетворяющих запросу не обнаруеженно.')

    print()
if __name__ == "__main__":
    while (True):
        main()
