import aiohttp
from loguru import logger
import config
import storage

CLIENT_TIMEOUT = aiohttp.ClientTimeout(total=10)


async def get_auth_headers(vk_id: int):
    token = await storage.get_token(vk_id)
    if not token: return {}
    token = token.strip().strip('"').strip("'")
    logger.debug(f"[VK: {vk_id}] Использую токен из Redis. Длина: {len(token)}. Начинается на: {token[:10]}")
    if not token.startswith("Beaver "):
        return {"Authorization" : f"Beaver {token}"}
    return {"Authorization": f"{token}"}


async def register_user(vk_id: int, username: str, password: str):
    url = f"{config.API_URL}/auth/register"
    payload = {
        "username": username,
        "password": password,
        "avatar_url": f"https://api.dicebear.com/7.x/thumbs/svg?seed={username}",
    }

    logger.debug(f"[VK: {vk_id}] POST запрос к {url} (регистрация: {username})")

    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get("access_token")
                    await storage.save_token(vk_id, token)
                    logger.success(
                        f"[VK: {vk_id}] Регистрация успешна! Токен сохранен ({username})"
                    )
                    return "Регистрация прошла успешно! Вы сразу авторизованы в боте."
                elif response.status == 400:
                    logger.warning(
                        f"[VK: {vk_id}] Ошибка 400 при регистрации: логин '{username}' занят или пароль простой"
                    )
                    return "Ошибка 400: Возможно, такой логин уже занят или пароль слишком простой."

                logger.error(
                    f"[VK: {vk_id}] Неожиданная ошибка сервера при регистрации: {response.status}"
                )
                return f"Неожиданная ошибка сервера: {response.status}"
        except Exception as e:
            logger.exception(f"[VK: {vk_id}] Сетевая ошибка при регистрации: {e}")
            return f"Ошибка сети: {e}"


async def login(vk_id: int, username: str, password: str):
    url = f"{config.API_URL}/auth/sign-in"

    logger.debug(f"[VK: {vk_id}] POST запрос к {url} (логин: {username})")

    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        try:
            async with session.post(
                url, json={"username": username, "password": password}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    await storage.save_token(vk_id, data.get("access_token"))
                    logger.success(f"[VK: {vk_id}] Успешная авторизация ({username})")
                    return "Успешная авторизация! Токен сохранен."

                logger.warning(
                    f"[VK: {vk_id}] Ошибка авторизации. Код API: {response.status}"
                )
                return f"Ошибка авторизации: {response.status} (Проверьте логин/пароль)"
        except Exception as e:
            logger.exception(f"[VK: {vk_id}] Сетевая ошибка при логине: {e}")
            return f"Ошибка соединения: {e}"


async def fetch_and_cache_tasks(vk_id: int):
    token = await storage.get_token(vk_id)
    quest_id = await storage.get_active_quest(vk_id)

    if not token:
        logger.warning(f"[VK: {vk_id}] Попытка запросить задания без токена")
        return "Нет токена. Напиши !логин <user> <pass> или !рега <user> <pass>"

    if not quest_id:
        logger.warning(f"[VK: {vk_id}] Попытка запросить задания без выбранного квеста")
        return "Выбери квест: !квест <ID>"

    headers = await get_auth_headers(vk_id)
    url = f"{config.API_URL}/quest/{quest_id}/play"

    logger.debug(f"[VK: {vk_id}] GET запрос к {url} (получение заданий)")

    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 401:
                    logger.warning(f"[VK: {vk_id}] Токен устарел (ошибка 401)")
                    return "Токен устарел или неверный. Получи новый на сайте и напиши: !токен <токен>"

                if response.status != 200:
                    logger.error(
                        f"[VK: {vk_id}] Ошибка получения заданий: {response.status}"
                    )
                    return f"Ошибка получения заданий: {response.status}"

                data = await response.json()
                task_groups = data.get("task_groups", [])

                await storage.clear_tasks(vk_id)

                task_counter = 1
                msg_lines = ["АКТУАЛЬНЫЕ ЗАДАНИЯ:\n"]

                for group in task_groups:
                    group_name = group.get("name", "Без названия")
                    for task in group.get("tasks", []):
                        if task.get("accepted"):
                            continue

                        real_uuid = task.get("id")
                        await storage.save_task(vk_id, task_counter, real_uuid)

                        name = task.get("name", "Безымянное")
                        question = task.get("question", "Без вопроса")
                        score = task.get("score", 0)

                        msg_lines.append(
                            f"[{task_counter}] {group_name} | {name} ({score} очков)"
                        )
                        msg_lines.append(f"Вопрос: {question}")

                        hints = task.get("hints", [])
                        for i, hint in enumerate(hints):
                            hint_num = i + 1
                            if hint.get("taken"):
                                msg_lines.append(
                                    f"   Подсказка {hint_num}: {hint.get('text')}"
                                )
                            else:
                                penalty = hint.get("penalty", {})
                                pen_str = "бесплатно"
                                if "score" in penalty:
                                    pen_str = f"-{penalty['score']} очков"
                                elif "percent" in penalty:
                                    pen_str = f"-{penalty['percent']}%"

                                msg_lines.append(
                                    f"   Подсказка {hint_num} доступна (Штраф: {pen_str})"
                                )

                        links = task.get("media_links", [])
                        if links:
                            msg_lines.append(f"Ссылки: {', '.join(links)}")
                        msg_lines.append("")
                        task_counter += 1

                if task_counter == 1:
                    logger.info(
                        f"[VK: {vk_id}] Задания получены, но все уже решены или их нет"
                    )
                    return "Заданий нет или все решены!"

                logger.success(
                    f"[VK: {vk_id}] Задания успешно получены и закэшированы (выдано: {task_counter - 1} шт)"
                )
                return "\n".join(msg_lines)
        except Exception as e:
            logger.exception(f"[VK: {vk_id}] Сетевая ошибка при получении заданий: {e}")
            return f"Ошибка сети: {e}"


async def submit_answer(vk_id: int, short_id: str, answer_text: str):
    quest_id = await storage.get_active_quest(vk_id)
    if not quest_id:
        logger.warning(f"[VK: {vk_id}] Попытка отправить ответ без выбранного квеста")
        return "Выбери квест: !квест <ID>"

    real_uuid = await storage.get_task(vk_id, short_id)
    if not real_uuid:
        logger.warning(f"[VK: {vk_id}] Задание [{short_id}] не найдено в кэше")
        return f"Задания [{short_id}] нет в списке. Напиши !задания"

    headers = await get_auth_headers(vk_id)
    if not headers:
        logger.warning(f"[VK: {vk_id}] Попытка ответить без токена")
        return "Нет токена, напиши !логин"

    url = f"{config.API_URL}/quest/{quest_id}/answer"
    payload = {"taskID": real_uuid, "text": answer_text}

    logger.debug(
        f"[VK: {vk_id}] POST запрос к {url} (ответ '{answer_text}' на задание {real_uuid})"
    )

    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("accepted"):
                        await storage.remove_task(vk_id, short_id)
                        logger.success(
                            f"[VK: {vk_id}] Ответ '{answer_text}' ПРИНЯТ (+{data.get('score')} очков)"
                        )
                        return f"ВЕРНО! (+{data.get('score')} очков)"

                    logger.info(f"[VK: {vk_id}] Ответ '{answer_text}' НЕВЕРНЫЙ")
                    return "Неверно."

                logger.error(
                    f"[VK: {vk_id}] Ошибка сервера при ответе: {response.status}"
                )
                return f"Ошибка сервера: {response.status}"
        except Exception as e:
            logger.exception(f"[VK: {vk_id}] Ошибка сети при отправке ответа: {e}")
            return f"Ошибка сети: {e}"


async def take_hint(vk_id: int, short_id: str, hint_index: int):
    quest_id = await storage.get_active_quest(vk_id)
    if not quest_id:
        logger.warning(f"[VK: {vk_id}] Попытка взять подсказку без выбранного квеста")
        return "Выбери квест: !квест <ID>"

    real_uuid = await storage.get_task(vk_id, short_id)
    if not real_uuid:
        logger.warning(
            f"[VK: {vk_id}] Задание [{short_id}] не найдено в кэше (подсказка)"
        )
        return f"Задания [{short_id}] нет в списке. Обнови список (!задания)"

    headers = await get_auth_headers(vk_id)
    if not headers:
        logger.warning(f"[VK: {vk_id}] Попытка взять подсказку без токена")
        return "Нет токена, напиши !логин"

    url = f"{config.API_URL}/quest/{quest_id}/hint"

    api_index = hint_index - 1

    payload = {"task_id": real_uuid, "index": api_index}

    logger.debug(
        f"[VK: {vk_id}] POST запрос к {url} (вскрытие подсказки {hint_index} для задания {real_uuid})"
    )

    async with aiohttp.ClientSession(timeout=CLIENT_TIMEOUT) as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    text = data.get("text", "Нет текста")
                    logger.success(
                        f"[VK: {vk_id}] Подсказка {hint_index} успешно вскрыта"
                    )
                    return f"ПОДСКАЗКА {hint_index} ВСКРЫТА!\nТекст: {text}"
                elif response.status == 406:
                    logger.warning(
                        f"[VK: {vk_id}] Подсказка {hint_index} уже взята или недоступна (406)"
                    )
                    return "Ошибка: Подсказка уже взята или такого номера нет."

                logger.error(
                    f"[VK: {vk_id}] Ошибка сервера при взятии подсказки: {response.status}"
                )
                return f"Ошибка сервера: {response.status}"
        except Exception as e:
            logger.exception(f"[VK: {vk_id}] Ошибка сети при взятии подсказки: {e}")
            return f"Ошибка сети: {e}"
