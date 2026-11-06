import telebot
import vk_api
import re
import time
import os
import builtins
import asyncio
import traceback
import aiohttp
import inspect
import threading
from flask import Flask
from maxapi import Bot

# --- ХАК ДЛЯ ПРИНУДИТЕЛЬНОГО ВЫВОДА ЛОГОВ В RENDER ---
def print(*args, **kwargs):
    kwargs['flush'] = True
    builtins.print(*args, **kwargs)
# -----------------------------------------------------

# ================= КОНФИГУРАЦИЯ TELEGRAM И ВКОНТАКТЕ =================
TG_TOKEN = '9090865881:AAFyB3mawPjgSINuLQSO3LRwizUREnA7dMI'

VK_READ_TOKEN = 'vk1.a.UQQypBdwlUwwk6O3z7iJAXc8Tnzx6VcB3seRHXgioyrLDLW-xYTXy7SCqONeAc7FOuadlIg1u52uEVFGrKvjCZmV-wq70J2TG_MqZKtn7aXkudTIrURT-OG2bzB1neTWwkHAM-buqJIWLYT8ioGLy6EiL84LamSMjstFgw1ynkXR_sCGZsspN2zbF5P9chaLu98ONjvbDVGk67_j1-CURw'
USER_TOKEN = 'vk1.a.j5kZmVp_KXZwjYWkBoLw4yeCxNbMktFGvI1DKZVAKVpdieHxtLGWwa-NC5s9BLaR28CkI15GxpdkPvr8KTwnqAdpEppxYINIQ56e3wPwjO-WVPV5vMUC7uCP4dhIdyJ5kvVMZiTHYmVUt-_-mCb0QV4sXLetc2b9OAh1jG2akxPxrdMa2ndtUpscCn_DVHNrkuRBTuMjBDmvBx00KTkcVQ'

# --- НАСТРОЙКИ АВТОПОСТЕРА ---
DONOR_GROUP_ID = -204081884  # ID Министерства образования и науки ЧР
CHECK_INTERVAL = 60          # Проверка новых постов каждые 60 секунд
# -----------------------------

TARGET_VK_GROUPS = [-215578086, -221202163, -219647526, -219649455, -215622579]

# ================= КОНФИГУРАЦИЯ МЕССЕНДЖЕРА МАКС ====================
MAX_BOT_TOKEN = 'f9LHodD0cOL81vMNbHAKhY6E8unklP9ERiZH1WN4qu0gTsUj1Dl6p6FUEd9OiiPXcvebPXREXcVP684jEawY'
TARGET_MAX_CHANNELS = ['-69296966003283', '-69205136755442', '-69209774882901', '-69207050491139', '-69224752493851']
# ====================================================================

bot = telebot.TeleBot(TG_TOKEN)

vk_read_session = vk_api.VkApi(token=VK_READ_TOKEN)
vk_read = vk_read_session.get_api()

vk_admin_session = vk_api.VkApi(token=USER_TOKEN)
vk_admin = vk_admin_session.get_api()

def get_max_photo_url(sizes):
    max_size, max_url = 0, ""
    for size in sizes:
        if size['height'] * size['width'] > max_size:
            max_size = size['height'] * size['width']
            max_url = size['url']
    return max_url

def extract_vk_attachments(post):
    attachments = []
    if 'attachments' in post:
        for att in post['attachments']:
            att_type = att['type']
            if att_type in ['photo', 'video', 'doc', 'audio']:
                item = att[att_type]
                att_str = f"{att_type}{item['owner_id']}_{item['id']}"
                if 'access_key' in item:
                    att_str += f"_{item['access_key']}"
                attachments.append(att_str)
    return ','.join(attachments)

def publish_to_vk_targets(text, attachments_str):
    vk_success_count = 0
    error_msgs = []
    for group_id in TARGET_VK_GROUPS:
        try:
            vk_admin.wall.post(
                owner_id=group_id,
                message=text,
                attachments=attachments_str,
                from_group=1
            )
            vk_success_count += 1
            time.sleep(2)
        except Exception as e:
            error_msgs.append(f"ВК {group_id}: {e}")
    return vk_success_count, error_msgs

async def download_and_send_media(max_bot, media_url, channel_id, caption=""):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(media_url) as response:
                if response.status == 200:
                    media_data = await response.read()
                    temp_filename = f"temp_{channel_id}_{int(time.time())}.jpg"
                    
                    with open(temp_filename, 'wb') as f:
                        f.write(media_data)
                        
                    success = False
                    
                    for func_name in ['upload_media', 'upload_file', 'upload_file_buffer']:
                        if success: break
                        func = getattr(max_bot, func_name, None)
                        if not func: continue
                        
                        try:
                            sig = inspect.signature(func)
                            kwargs = {}
                            chat_key = file_key = caption_key = None
                            
                            for p in sig.parameters:
                                pl = p.lower()
                                if 'chatid' in pl or 'peer' in pl or p == 'to' or p == 'id': chat_key = p
                                elif 'file' in pl or 'media' in pl or 'photo' in pl: file_key = p
                                elif 'caption' in pl or 'text' in pl: caption_key = p
                                
                            if chat_key and file_key:
                                kwargs[chat_key] = channel_id
                                try:
                                    with open(temp_filename, 'rb') as f_obj:
                                        kwargs[file_key] = f_obj
                                        if caption_key and caption:
                                            kwargs[caption_key] = caption
                                            await func(**kwargs)
                                            success = True
                                        else:
                                            await func(**kwargs)
                                            if caption: await max_bot.send_message(chat_id=channel_id, text=caption)
                                            success = True
                                except Exception: pass
                        except Exception: pass

                    if not success:
                        try:
                            with open(temp_filename, 'rb') as f_obj:
                                file_resp = await max_bot.upload_file(file=f_obj)
                            if file_resp:
                                try:
                                    await max_bot.send_message(chat_id=channel_id, text=caption, attachments=[file_resp])
                                    success = True
                                except Exception:
                                    await max_bot.send_message(chat_id=channel_id, text=caption, file=file_resp)
                                    success = True
                        except Exception: pass

                    if not success:
                        for func_name in ['upload_media', 'upload_file']:
                            if success: break
                            func = getattr(max_bot, func_name, None)
                            if func:
                                try:
                                    with open(temp_filename, 'rb') as f_obj:
                                        await func(channel_id, f_obj)
                                    if caption: await max_bot.send_message(chat_id=channel_id, text=caption)
                                    success = True
                                except Exception: pass

                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                            
                    return success
    except Exception as e: 
        print(f"[Ошибка сети]: {e}")
        return False

async def process_post_to_max(post):
    max_bot = Bot(token=MAX_BOT_TOKEN)
    post_text = post.get('text', '')
    photos = []
    videos = []

    if 'attachments' in post:
        for att in post['attachments']:
            if att['type'] == 'photo':
                photos.append(get_max_photo_url(att['photo']['sizes']))
            elif att['type'] == 'video':
                video_owner = att['video']['owner_id']
                video_id = att['video']['id']
                videos.append(f"https://vk.com/video{video_owner}_{video_id}")

    if videos:
        post_text += "\n\n🎥 Видео:\n" + "\n".join(videos)

    max_length = 3900 
    if len(post_text) > max_length:
        cut_index = max(
            post_text.rfind('.', 0, max_length), 
            post_text.rfind('!', 0, max_length), 
            post_text.rfind('?', 0, max_length)
        )
        if cut_index != -1: post_text = post_text[:cut_index + 1]
        else:
            cut_index = post_text.rfind(' ', 0, max_length)
            if cut_index != -1: post_text = post_text[:cut_index] + "..."
            else: post_text = post_text[:max_length] + "..."
                
    post_text = post_text.strip()

    for channel_id in TARGET_MAX_CHANNELS:
        try:
            if photos:
                success = await download_and_send_media(max_bot, photos[0], channel_id, caption=post_text)
                if not success and post_text:
                    await max_bot.send_message(chat_id=channel_id, text=post_text)
                elif success:
                    for photo_url in photos[1:]:
                        await asyncio.sleep(1)
                        await download_and_send_media(max_bot, photo_url, channel_id, caption="")
            else:
                if post_text:
                    await max_bot.send_message(chat_id=channel_id, text=post_text)
            await asyncio.sleep(2) 
        except Exception as e: 
            print(f"[Ошибка МАКС канал {channel_id}]: {e}")

# ================== ФОНОВЫЙ АВТОПОСТЕР ==================
def auto_poster_loop():
    print(f"Автопостер запущен! Слежу за группой {DONOR_GROUP_ID}...")
    
    memory_file = "last_post.txt"
    last_post_id = 0
    
    if os.path.exists(memory_file):
        with open(memory_file, "r") as f:
            content = f.read().strip()
            if content.isdigit():
                last_post_id = int(content)

    while True:
        try:
            response = vk_read.wall.get(owner_id=DONOR_GROUP_ID, count=5)
            posts = response['items']
            posts = sorted(posts, key=lambda x: x['id'])
            
            for post in posts:
                if post['id'] > last_post_id:
                    if last_post_id == 0:
                        last_post_id = post['id']
                        continue
                        
                    print(f"\n[АВТОПОСТЕР] Найден новый пост ID {post['id']}! Начинаю рассылку...")
                    
                    text = post.get('text', '')
                    attachments_str = extract_vk_attachments(post)
                    
                    vk_success, vk_errs = publish_to_vk_targets(text, attachments_str)
                    print(f"[АВТОПОСТЕР] ВК: Успешно {vk_success}/{len(TARGET_VK_GROUPS)}")
                    if vk_errs: print(f"Ошибки ВК: {vk_errs}")
                    
                    try:
                        asyncio.run(process_post_to_max(post))
                        print(f"[АВТОПОСТЕР] МАКС: Обработка завершена")
                    except Exception as max_err:
                        print(f"[АВТОПОСТЕР Ошибка МАКС]: {max_err}")
                        
                    last_post_id = post['id']
                    with open(memory_file, "w") as f:
                        f.write(str(last_post_id))
                        
        except Exception as e:
            print(f"[Ошибка Автопостера]: {e}")
            
        time.sleep(CHECK_INTERVAL)

# ================== ФЕЙКОВЫЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ==================
app = Flask(__name__)

@app.route('/')
def keep_alive():
    return "Bot is alive and working!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ================= ОСНОВНАЯ ЛОГИКА TELEGRAM =================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Автопостер работает в фоне. Если хочешь выложить пост вне очереди, просто пришли мне ссылку на него.")

@bot.message_handler(func=lambda message: 'vk.com/wall' in message.text)
def handle_vk_link(message):
    match = re.search(r'wall(-?\d+_\d+)', message.text)
    if not match:
        bot.reply_to(message, "❌ Не удалось распознать ID поста в ссылке.")
        return
        
    post_id = match.group(1)
    bot.reply_to(message, f"⏳ Обрабатываю пост {post_id} вручную...")
    
    try:
        response = vk_read.wall.getById(posts=post_id)
        if not response:
            bot.reply_to(message, "❌ Пост не найден или закрыт.")
            return
            
        post = response[0]
        text = post.get('text', '')
        attachments_str = extract_vk_attachments(post)
        
        bot.send_message(message.chat.id, "▶️ Начинаю публикацию во ВКонтакте...")
        vk_success, error_msgs = publish_to_vk_targets(text, attachments_str)
                
        bot.send_message(message.chat.id, "▶️ Начинаю перенос галереи и текста в мессенджер МАКС...")
        try:
            asyncio.run(process_post_to_max(post))
        except Exception as max_err:
            print(f"[Критическая ошибка МАКС]: {max_err}")

        result_msg = f"✅ Готово!\n\n🔵 ВКонтакте: {vk_success} из {len(TARGET_VK_GROUPS)} групп.\n🟢 МАКС: Обработка завершена."
        if error_msgs: result_msg += "\n\n⚠️ Ошибки ВК:\n" + "\n".join(error_msgs)
        bot.send_message(message.chat.id, result_msg)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Произошла общая ошибка: {e}")

if __name__ == '__main__':
    try:
        # 1. Запускаем веб-сервер для обхода лимитов Render
        threading.Thread(target=run_web, daemon=True).start()
        
        # 2. Запускаем автопостер ВК в фоновом режиме
        threading.Thread(target=auto_poster_loop, daemon=True).start()
        
        # 3. Запускаем Telegram-бота для ручного контроля
        print("Телеграм-бот и автопостер успешно запущены...")
        bot.infinity_polling()
    except BaseException as e:
        print("\n=== ПРОИЗОШЛА КРИТИЧЕСКАЯ ОШИБКА РАБОТЫ ===")
        traceback.print_exc()
        input("\nНажмите Enter, чтобы закрыть окно...")
