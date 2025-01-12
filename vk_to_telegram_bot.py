import requests
import asyncio
from telegram import Bot, InputMediaPhoto
import time
import traceback
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Ваш токен бота
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")  # Ваш сервисный ключ VK
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # Ваш канал в Telegram
VK_GROUP_ID = os.getenv("VK_GROUP_ID")  # ID вашей группы VK
CHECK_INTERVAL = 60  # Интервал проверки постов (в секундах)
RETRY_INTERVAL = 120  # Интервал между попытками при ошибках VK API (в секундах)

# Инициализация бота Telegram
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Хранение ID последнего поста
last_post_id = None

async def get_vk_posts():
    """Получить последние посты из VK, исключая закрепленные."""
    try:
        url = f"https://api.vk.com/method/wall.get?owner_id={VK_GROUP_ID}&count=10&filter=all&access_token={VK_ACCESS_TOKEN}&v=5.131"
        response = requests.get(url).json()

        # Проверяем на ошибку в ответе VK
        if 'error' in response:
            if response['error']['error_code'] == 10:  # Код ошибки 10 - временная ошибка на стороне сервера VK
                print("Ошибка VK API: Временная ошибка, повторная попытка...")
                await asyncio.sleep(RETRY_INTERVAL)
                return await get_vk_posts()  # Повторный запрос
            else:
                raise ValueError(f"Ошибка VK API: {response['error']}")

        # Проверка, если нет постов
        if 'response' in response and 'items' in response['response']:
            posts = response['response']['items']
            # Исключаем закрепленные посты (если это не последний)
            posts = [post for post in posts if not post.get('is_pinned', False)]
            return posts
        else:
            return []
    except Exception as e:
        print(f"Ошибка при запросе VK API: {e}")
        traceback.print_exc()
        await asyncio.sleep(RETRY_INTERVAL)
        return await get_vk_posts()

async def send_to_telegram(text, attachments):
    """Отправить сообщение в Telegram с изображением в одном посте."""
    try:
        media = []

        # Если есть картинки, добавляем их в media
        for attachment in attachments:
            if attachment['type'] == 'photo':
                photo_url = attachment['photo']['sizes'][-1]['url']
                # Добавляем подпись к фотографии при создании объекта InputMediaPhoto
                media.append(InputMediaPhoto(media=photo_url, caption=text))

        # Если есть медиафайлы, отправляем их
        if media:
            await bot.send_media_group(chat_id=TELEGRAM_CHANNEL_ID, media=media)

        # Если текста нет, просто отправляем картинки
        elif text:
            # Используем Markdown для сохранения форматирования
            formatted_text = text.replace("\n", "\n\n")  # Два переноса строки для абзацев
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=formatted_text, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка при отправке в Telegram: {e}")
        traceback.print_exc()

async def main():
    global last_post_id
    while True:
        try:
            posts = await get_vk_posts()
            if posts:
                post = posts[0]
                post_id = post['id']
                if post_id != last_post_id:  # Новый пост
                    last_post_id = post_id
                    text = post.get('text', '')
                    attachments = post.get('attachments', [])
                    await send_to_telegram(text, attachments)
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            traceback.print_exc()
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        traceback.print_exc()
