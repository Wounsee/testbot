import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- Настройка бота ---
BOT_TOKEN = "8338120116:AAH8WfZuQR19ga4NU9WR4steHtrcL7q8g1o"  # Замените на ваш токен!
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Клавиатуры ---
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить слово"), KeyboardButton(text="📖 Показать слова")],
        [KeyboardButton(text="🎯 Тренировка"), KeyboardButton(text="❌ Удалить слово")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

training_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⏹️ Закончить тренировку")]
    ],
    resize_keyboard=True
)


# --- Состояния FSM ---
class AddWordState(StatesGroup):
    waiting_for_word = State()
    waiting_for_translation = State()


class DeleteWordState(StatesGroup):
    waiting_for_word = State()


class TrainingState(StatesGroup):
    in_training = State()


# --- Работа с данными ---
DATA_FILE = "user_vocabulary.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def add_word_to_user(user_id, english_word, translation):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {}
    data[str(user_id)][english_word.lower()] = translation.lower()
    save_data(data)


def get_user_words(user_id):
    data = load_data()
    return data.get(str(user_id), {})


def delete_user_word(user_id, english_word):
    data = load_data()
    user_data = data.get(str(user_id), {})
    if english_word.lower() in user_data:
        del user_data[english_word.lower()]
        data[str(user_id)] = user_data
        save_data(data)
        return True
    return False


# --- Обработчики команд ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Я бот для изучения английских слов.\n"
        "Используй кнопки ниже или команды:",
        reply_markup=main_keyboard
    )
    await message.answer(
        "📋 Доступные команды:\n"
        "/add - добавить слово\n"
        "/show - показать слова\n"
        "/train - начать тренировку\n"
        "/delete - удалить слово\n"
        "/help - помощь"
    )


@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: types.Message):
    help_text = (
        "📚 <b>Как пользоваться ботом:</b>\n\n"
        "➕ <b>Добавить слово:</b>\n"
        "   - Нажми кнопку '➕ Добавить слово'\n"
        "   - Или напиши /add\n"
        "   - Формат: слово - перевод\n\n"
        "📖 <b>Посмотреть слова:</b>\n"
        "   - Кнопка '📖 Показать слова'\n"
        "   - Команда /show\n\n"
        "🎯 <b>Тренировка:</b>\n"
        "   - Кнопка '🎯 Тренировка'\n"
        "   - Команда /train\n\n"
        "❌ <b>Удалить слово:</b>\n"
        "   - Кнопка '❌ Удалить слово'\n"
        "   - Команда /delete слово\n\n"
        "⚡ <b>Просто нажимай на кнопки!</b>"
    )
    await message.answer(help_text, parse_mode="HTML")


# --- Добавление слова ---
@dp.message(Command("add"))
@dp.message(F.text == "➕ Добавить слово")
async def cmd_add(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите слово и перевод в формате:\n"
        "<code>слово - перевод</code>\n\n"
        "Например: <code>apple - яблоко</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddWordState.waiting_for_word)


@dp.message(AddWordState.waiting_for_word)
async def process_add_word(message: types.Message, state: FSMContext):
    if ' - ' not in message.text:
        await message.answer("❌ Неправильный формат. Используйте: <code>слово - перевод</code>", parse_mode="HTML")
        return

    english_word, translation = message.text.split(' - ', 1)
    if not english_word.strip() or not translation.strip():
        await message.answer("❌ Слово и перевод не могут быть пустыми")
        return

    add_word_to_user(message.from_user.id, english_word.strip(), translation.strip())
    await message.answer(
        f"✅ Добавлено: <b>{english_word.strip()}</b> - <i>{translation.strip()}</i>",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )
    await state.clear()


# --- Показать слова ---
@dp.message(Command("show"))
@dp.message(F.text == "📖 Показать слова")
async def cmd_show(message: types.Message):
    user_words = get_user_words(message.from_user.id)

    if not user_words:
        await message.answer("📝 Ваш словарь пуст. Добавьте слова с помощью кнопки '➕ Добавить слово'")
        return

    response = "📚 <b>Ваш словарь:</b>\n\n"
    for word, translation in user_words.items():
        response += f"• <b>{word}</b> - <i>{translation}</i>\n"

    # Разбиваем сообщение если слишком длинное
    if len(response) > 4000:
        chunks = [response[i:i + 4000] for i in range(0, len(response), 4000)]
        for chunk in chunks:
            await message.answer(chunk, parse_mode="HTML")
    else:
        await message.answer(response, parse_mode="HTML")


# --- Удаление слова ---
@dp.message(Command("delete"))
@dp.message(F.text == "❌ Удалить слово")
async def cmd_delete(message: types.Message, state: FSMContext):
    user_words = get_user_words(message.from_user.id)

    if not user_words:
        await message.answer("📝 Нечего удалять - словарь пуст")
        return

    await message.answer(
        "Введите слово, которое хотите удалить:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(DeleteWordState.waiting_for_word)


@dp.message(DeleteWordState.waiting_for_word)
async def process_delete_word(message: types.Message, state: FSMContext):
    word_to_delete = message.text.strip().lower()
    success = delete_user_word(message.from_user.id, word_to_delete)

    if success:
        await message.answer(f"✅ Слово '<b>{word_to_delete}</b>' удалено", parse_mode="HTML")
    else:
        await message.answer(f"❌ Слово '<b>{word_to_delete}</b>' не найдено в вашем словаре", parse_mode="HTML")

    await state.clear()
    await message.answer("Выберите действие:", reply_markup=main_keyboard)


# --- Тренировка ---
@dp.message(Command("train"))
@dp.message(F.text == "🎯 Тренировка")
async def cmd_train(message: types.Message, state: FSMContext):
    user_words = get_user_words(message.from_user.id)

    if not user_words:
        await message.answer("📝 Для тренировки нужно сначала добавить слова")
        return

    # Сохраняем слова в состоянии
    await state.update_data(words=list(user_words.items()))
    await state.update_data(score=0)
    await state.update_data(total=len(user_words))

    await message.answer(
        "🎯 <b>Начинаем тренировку!</b>\n\n"
        "Я буду показывать английские слова, а вы вводите перевод.\n"
        "Для завершения нажмите '⏹️ Закончить тренировку'",
        parse_mode="HTML",
        reply_markup=training_keyboard
    )

    # Отправляем первое слово
    await send_next_word(message, state)
    await state.set_state(TrainingState.in_training)


async def send_next_word(message: types.Message, state: FSMContext):
    data = await state.get_data()
    words = data['words']

    if not words:
        # Тренировка завершена
        score = data['score']
        total = data['total']
        await message.answer(
            f"🏁 <b>Тренировка завершена!</b>\n\n"
            f"✅ Правильных ответов: <b>{score}/{total}</b>\n"
            f"📊 Результат: <b>{round(score / total * 100)}%</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard
        )
        await state.clear()
        return

    # Берем первое слово из списка
    current_word, current_translation = words[0]
    await state.update_data(
        current_word=current_word,
        current_translation=current_translation,
        words=words[1:]  # Убираем использованное слово
    )

    await message.answer(f"🔤 Как переводится слово: <b>{current_word}</b>?", parse_mode="HTML")


@dp.message(TrainingState.in_training)
async def handle_training_answer(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Закончить тренировку":
        data = await state.get_data()
        score = data.get('score', 0)
        total = data.get('total', 0)
        await message.answer(
            f"⏹️ <b>Тренировка прервана</b>\n\n"
            f"✅ Правильных ответов: <b>{score}/{total}</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard
        )
        await state.clear()
        return

    data = await state.get_data()
    correct_answer = data['current_translation']
    user_answer = message.text.strip().lower()

    if user_answer == correct_answer:
        await message.answer("✅ <b>Верно!</b>", parse_mode="HTML")
        await state.update_data(score=data['score'] + 1)
    else:
        await message.answer(f"❌ <b>Неверно!</b>\nПравильный ответ: <i>{correct_answer}</i>", parse_mode="HTML")

    # Отправляем следующее слово
    await send_next_word(message, state)


# --- Запуск бота ---
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
