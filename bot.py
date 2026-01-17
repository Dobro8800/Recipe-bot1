import os
import requests
import asyncio
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message
from aiogram.dispatcher.filters import CommandStart

# ================== Настройки ==================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5"

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

# ================== FSM ==================
class RecipeForm(StatesGroup):
    persons = State()
    time = State()
    ingredients = State()

# ================== Start ==================
@dp.message_handler(commands=["start"])
async def start(message: Message):
    await RecipeForm.persons.set()
    await message.answer(
        "👋 Привет! Я помогу решить, что приготовить сегодня 🍽\n"
        "Сначала скажи, сколько человек будет есть?"
    )

# ================== Persons ==================
@dp.message_handler(state=RecipeForm.persons)
async def get_persons(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❗ Введи число, например: 2")
        return
    await state.update_data(persons=message.text)
    await RecipeForm.next()
    await message.answer("⏱ Сколько минут есть на готовку?")

# ================== Time ==================
@dp.message_handler(state=RecipeForm.time)
async def get_time(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❗ Введи число минут, например: 30")
        return
    await state.update_data(time=message.text)
    await RecipeForm.next()
    await message.answer("🧺 Какие продукты есть в холодильнике?\nПример: курица, картофель, лук")

# ================== Ingredients + Gemini ==================
@dp.message_handler(state=RecipeForm.ingredients)
async def get_ingredients(message: Message, state: FSMContext):
    await state.update_data(ingredients=message.text)
    data = await state.get_data()
    await message.answer("🤖 Генерирую рецепт...")

    recipe = generate_recipe_gemini(
        persons=data["persons"],
        time=data["time"],
        ingredients=data["ingredients"]
    )

    await message.answer(recipe)
    await state.finish()

# ================== Gemini API ==================
def generate_recipe_gemini(persons, time, ingredients):
    prompt = f"""
Придумай простой рецепт. Условия:
- Количество человек: {persons}
- Время готовки: {time} минут
- Используй только эти продукты: {ingredients}

Формат:
Название блюда
⏱ Время
👥 Порции

Ингредиенты:
- список

Приготовление:
1. шаги

Не более 120 слов.
"""
    url = "https://api.gemini.com/v1/generate"  # уточни актуальный endpoint
    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GEMINI_MODEL, "prompt": prompt, "temperature": 0.7, "max_output_tokens": 300}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("text", "Не удалось сгенерировать рецепт.")
    except Exception as e:
        return f"Произошла ошибка при генерации рецепта: {e}"

# ================== Run ==================
async def main():
    print("🤖 Бот запущен")
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
