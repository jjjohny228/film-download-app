from bot.keyboards.reply import main_menu_kb
from bot.keyboards.inline import carousel_kb, quality_kb, seasons_kb, episodes_kb


def test_main_menu_user_has_two_buttons():
    kb = main_menu_kb(is_admin=False)
    buttons = [btn.text for row in kb.keyboard for btn in row]
    assert "🔍 Найти фильм" in buttons
    assert "👤 Профиль" in buttons
    assert "📢 Рассылка" not in buttons


def test_main_menu_admin_has_admin_buttons():
    kb = main_menu_kb(is_admin=True)
    buttons = [btn.text for row in kb.keyboard for btn in row]
    assert "📢 Рассылка" in buttons
    assert "📊 Статистика" in buttons
    assert "🌐 Загрузить прокси" in buttons


def test_carousel_kb_shows_correct_counter():
    kb = carousel_kb(idx=2, total=8)
    all_text = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "2/8" in all_text


def test_quality_kb_has_three_options():
    kb = quality_kb()
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("480" in t for t in buttons)
    assert any("720" in t for t in buttons)
    assert any("1080" in t for t in buttons)


def test_seasons_kb_rows_of_three():
    seasons = {1: [1, 2], 2: [1, 2, 3], 3: [1], 4: [1]}
    kb = seasons_kb(seasons)
    # First row should have 3 buttons
    assert len(kb.inline_keyboard[0]) == 3


def test_episodes_kb_rows_of_five():
    episodes = list(range(1, 12))
    kb = episodes_kb(episodes, season=1)
    assert len(kb.inline_keyboard[0]) == 5
    assert kb.inline_keyboard[0][0].callback_data == "ep:1:1"
