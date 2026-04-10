from vkbottle.bot import Bot, Message
from loguru import logger
import sys
import config
import quest_api
import storage


logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)
logger.add("logs/bot.log", rotation="5 MB", retention="10 days", level="INFO")

bot = Bot(token=config.VK_TOKEN)


@bot.on.message(text="!рега <username> <password>")
async def register_handler(message: Message, username: str, password: str):
    vk_id = message.from_id
    logger.info(f"[VK: {vk_id}] Запросил регистрацию аккаунта '{username}'")
    await message.answer("Создаю аккаунт...")
    result = await quest_api.register_user(vk_id, username, password)
    await message.answer(result)


@bot.on.message(text="!логин <username> <password>")
async def login_handler(message: Message, username: str, password: str):
    vk_id = message.from_id
    logger.info(f"[VK: {vk_id}] Пытается войти в аккаунт '{username}'")
    await message.answer("Пробую войти...")
    result = await quest_api.login(vk_id, username, password)
    await message.answer(result)


@bot.on.message(text="!квест <quest_id>")
async def set_quest_handler(message: Message, quest_id: str):
    vk_id = message.from_id
    logger.info(f"[VK: {vk_id}] Устанавливает активный квест: {quest_id}")
    await storage.save_active_quest(vk_id, quest_id)
    await message.answer(
        f"Квест {quest_id} установлен для тебя!\nТеперь напиши !задания"
    )


@bot.on.message(text="!задания")
async def tasks_handler(message: Message):
    vk_id = message.from_id
    logger.info(f"[VK: {vk_id}] Запросил список заданий")
    await message.answer("Запрашиваю список заданий...")
    result = await quest_api.fetch_and_cache_tasks(vk_id)
    await message.answer(result)


@bot.on.message(text="!ответ <short_id> <ans>")
async def answer_handler(message: Message, short_id: str, ans: str):
    vk_id = message.from_id
    logger.info(f"[VK: {vk_id}] Отправляет ответ '{ans}' на задание [{short_id}]")
    await message.answer(f"Проверяю ответ на задание [{short_id}]...")
    result = await quest_api.submit_answer(vk_id, short_id, ans)
    await message.answer(result)


@bot.on.message(text="!подсказка <short_id> <hint_index>")
async def hint_handler(message: Message, short_id: str, hint_index: str):
    vk_id = message.from_id
    logger.info(
        f"[VK: {vk_id}] Запрашивает подсказку {hint_index} для задания [{short_id}]"
    )
    if not hint_index.isdigit():
        await message.answer("Номер подсказки должен быть цифрой!")
        return

    await message.answer(f"Вскрываю подсказку {hint_index}...")
    result = await quest_api.take_hint(vk_id, short_id, int(hint_index))
    await message.answer(result)


@bot.on.message(text=["!помощь", "начать", "help", "привет"])
async def help_handler(message: Message):
    vk_id = message.from_id
    logger.info(f"[VK: {vk_id}] Запросил меню помощи")
    text = (
        "ДОСТУПНЫЕ КОМАНДЫ:\n\n"
        "АККАУНТ:\n"
        "!рега <логин> <пароль>\n"
        "!логин <логин> <пароль> — если вход не через Google\n"
        "!токен <твой_токен> — если вход через Google (вставить из браузера)\n\n"
        "ИГРА:\n"
        "!квест <ID>\n"
        "!задания\n"
        "!ответ <номер_задания> <текст>\n"
        "!подсказка <номер_задания> <номер_подсказки>\n"
    )
    await message.answer(text)

@bot.on.message(text="!токен <token>")
async def token_handler(message: Message, token: str):
    vk_id = message.from_id
    logger.info(f"[VK: {vk_id}] Установил токен вручную")
    await storage.save_token(vk_id, token)
    await message.answer("Токен успешно сохранен! Теперь ты можешь выбрать квест через !квест <ID>")


if __name__ == "__main__":
    logger.success("Бот запущен юху!")
    bot.run_forever()
