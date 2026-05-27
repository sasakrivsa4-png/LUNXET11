import os, asyncio, io
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

TOKEN  = os.getenv("BOT_TOKEN")
SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_SERVICE_KEY")

bot = Bot(token=TOKEN)
dp  = Dispatcher()
sb  = create_client(SB_URL, SB_KEY)

# ─────────────────────────────────────
class ShopStates(StatesGroup):
    add_name    = State()
    add_price   = State()
    add_cat     = State()
    add_desc    = State()
    add_sizes   = State()
    add_images  = State()
    delete_mode = State()

# ─────────────────────────────────────
def get_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="➕ Додати товар"),
            KeyboardButton(text="🗑️ Видалити товар")
        ]],
        resize_keyboard=True
    )

def get_cat_kb():
    cats = ["Верхній одяг", "Кофти", "Штани", "Аксесуари", "Взуття"]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=c)] for c in cats],
        resize_keyboard=True
    )

def get_sizes_kb():
    sizes = ["S", "M", "L", "XL", "Універсальний", "Вписати свій ✏️"]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=s)] for s in sizes],
        resize_keyboard=True
    )

async def get_delete_kb():
    result = sb.table('products').select('name').eq('active', True).execute()
    products = result.data or []
    if not products:
        return None
    buttons = [[KeyboardButton(text=p['name'])] for p in products]
    buttons.append([KeyboardButton(text="❌ Скасувати")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ─────────────────────────────────────
#  Завантаження фото в Supabase Storage
# ─────────────────────────────────────
async def upload_photo(file_id: str) -> str:
    file = await bot.get_file(file_id)
    buf  = io.BytesIO()
    await bot.download_file(file.file_path, buf)
    buf.seek(0)
    filename = f"products/{file_id}.jpg"
    sb.storage.from_("product-images").upload(
        filename,
        buf.read(),
        {"content-type": "image/jpeg", "upsert": "true"}
    )
    return sb.storage.from_("product-images").get_public_url(filename)

# ─────────────────────────────────────
#  /start
# ─────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Менеджер магазину активований.", reply_markup=get_main_kb())

# ─────────────────────────────────────
#  ВИДАЛЕННЯ
# ─────────────────────────────────────
@dp.message(F.text == "🗑️ Видалити товар")
async def start_delete(m: Message, state: FSMContext):
    await state.clear()
    kb = await get_delete_kb()
    if kb is None:
        return await m.answer("Список товарів порожній, нічого видаляти.", reply_markup=get_main_kb())
    await m.answer("Оберіть товар зі списку для видалення:", reply_markup=kb)
    await state.set_state(ShopStates.delete_mode)

@dp.message(ShopStates.delete_mode)
async def process_delete(m: Message, state: FSMContext):
    if m.text == "❌ Скасувати":
        await state.clear()
        return await m.answer("Видалення скасовано.", reply_markup=get_main_kb())

    name_to_delete = m.text
    result = sb.table('products').update({'active': False}).eq('name', name_to_delete).execute()

    if result.data:
        await m.answer(f"✅ Товар '{name_to_delete}' видалено з сайту!", reply_markup=get_main_kb())
    else:
        await m.answer(f"⚠️ Товар '{name_to_delete}' не знайдено.", reply_markup=get_main_kb())

    await state.clear()

# ─────────────────────────────────────
#  ДОДАВАННЯ
# ─────────────────────────────────────
@dp.message(F.text == "➕ Додати товар")
async def start_add(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("1. Введіть назву товару:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ShopStates.add_name)

@dp.message(ShopStates.add_name)
async def add_n(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("2. Оберіть категорію:", reply_markup=get_cat_kb())
    await state.set_state(ShopStates.add_cat)

@dp.message(ShopStates.add_cat)
async def add_c(m: Message, state: FSMContext):
    await state.update_data(category=m.text.lower())
    await m.answer("3. Введіть ціну цифрами:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ShopStates.add_price)

@dp.message(ShopStates.add_price)
async def add_p(m: Message, state: FSMContext):
    if not m.text.isdigit():
        return await m.answer("Будь ласка, введіть число!")
    await state.update_data(price=int(m.text))
    await m.answer("4. Введіть опис товару:")
    await state.set_state(ShopStates.add_desc)

@dp.message(ShopStates.add_desc)
async def add_d(m: Message, state: FSMContext):
    await state.update_data(description=m.text)
    await m.answer("5. Оберіть розмір:", reply_markup=get_sizes_kb())
    await state.set_state(ShopStates.add_sizes)

@dp.message(ShopStates.add_sizes)
async def add_s(m: Message, state: FSMContext):
    if m.text == "Вписати свій ✏️":
        return await m.answer("Напишіть розміри через кому (напр: 36, 38, 40):")
    sizes = [s.strip() for s in m.text.replace("✏️", "").split(",") if s.strip()]
    await state.update_data(sizes=sizes)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ ГОТОВО")]], resize_keyboard=True)
    await m.answer("6. Надсилайте фото. Потім натисніть ✅ ГОТОВО", reply_markup=kb)
    await state.set_state(ShopStates.add_images)

@dp.message(ShopStates.add_images, F.photo)
async def add_i(m: Message, state: FSMContext):
    await m.answer("⏳ Завантажую фото…")
    try:
        url  = await upload_photo(m.photo[-1].file_id)
        data = await state.get_data()
        imgs = data.get('images', [])
        imgs.append(url)
        await state.update_data(images=imgs)
        await m.answer(f"📸 Додано фото ({len(imgs)})")
    except Exception as e:
        await m.answer(f"❌ Помилка завантаження: {e}")

@dp.message(ShopStates.add_images, F.text == "✅ ГОТОВО")
async def add_f(m: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get('images'):
        return await m.answer("Додайте хоча б одне фото!")

    try:
        sb.table('products').insert({
            'name':        data['name'],
            'price':       data['price'],
            'description': data.get('description', ''),
            'category':    data.get('category', ''),
            'sizes':       data.get('sizes', []),
            'images':      data.get('images', []),
            'active':      True
        }).execute()
        await m.answer("✅ Товар додано на сайт!", reply_markup=get_main_kb())
    except Exception as e:
        await m.answer(f"❌ Помилка збереження: {e}", reply_markup=get_main_kb())

    await state.clear()

# ─────────────────────────────────────
async def main():
    print("Бот запущений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
