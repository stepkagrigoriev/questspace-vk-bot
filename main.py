from vkbottle.bot import Bot, Message
import config
import quest_api
import storage

bot = Bot(token=config.VK_TOKEN)


@bot.on.message(text="!логин <username> <password>")
async def login_handler(message: Message, username: str, password: str):
    vk_id = message.from_id
    await message.answer("Пробую войти...")
    result = await quest_api.login(vk_id, username, password)
    await message.answer(result)


@bot.on.message(text="!квест <quest_id>")
async def set_quest_handler(message: Message, quest_id: str):
    vk_id = message.from_id
    await storage.save_active_quest(vk_id, quest_id)
    await message.answer(f"Квест {quest_id} установлен для тебя!")


@bot.on.message(text="!ответ <short_id> <ans>")
async def answer_handler(message: Message, short_id: str, ans: str):
    vk_id = message.from_id
    await message.answer("Отправляю...")
    result = await quest_api.submit_answer(vk_id, short_id, ans)
    await message.answer(result)


@bot.on.message(text="!рега <username> <password>")
async def register_handler(message: Message, username: str, password: str):
    vk_id = message.from_id
    await message.answer("Создаю аккаунт...")

    result = await quest_api.register_user(vk_id, username, password)
    await message.answer(result)


@bot.on.message(text="!помощь")
async def help_handler(message: Message):
    text = (
        "ДОСТУПНЫЕ КОМАНДЫ:\n\n"
        "АККАУНТ:\n"
        "!рега <логин> <пароль> — создать новый аккаунт\n"
        "!логин <логин> <пароль> — войти в существующий\n\n"
        "ИГРА:\n"
        "!квест <ID> — выбрать квест\n"
        "!задания — получить список заданий\n"
        "!ответ <номер> <текст> — отправить ответ\n"
        "!подсказка <номер_задания> <номер_подсказки>\n"
    )
    await message.answer(text)


@bot.on.message(text="!подсказка <short_id> <hint_index>")
async def hint_handler(message: Message, short_id: str, hint_index: str):
    vk_id = message.from_id
    if not hint_index.isdigit():
        await message.answer("Номер подсказки должен быть цифрой!")
        return
    await message.answer("Запрашиваю подсказку...")
    result = await quest_api.take_hint(vk_id, short_id, int(hint_index))
    await message.answer(result)

@bot.on.message(text="!задания")
async def tasks_handler(message: Message):
    vk_id = message.from_id
    await message.answer("Запрашиваю список заданий...")
    result = await quest_api.fetch_and_cache_tasks(vk_id)
    await message.answer(result)

if __name__ == "__main__":
    print("бот работает юху")
    bot.run_forever()
