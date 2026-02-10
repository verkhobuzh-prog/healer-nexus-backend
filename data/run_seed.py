"""
Скрипт сіду: викликає load_initial_data() — 20 спеціалістів, блоги, портфоліо.
Коректно підключається до БД, показує прогрес українською.
Запуск з кореня проєкту: python -m data.run_seed
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Корінь проєкту в path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main() -> None:
    from app.admin.pre_seed_learning import load_initial_data

    def progress(i: int, total: int, name: str) -> None:
        print(f"  Створено спеціаліста {i}/{total}: {name}")

    try:
        result = await load_initial_data(progress_callback=progress)
        print()
        print("  Підсумок:")
        print(f"  Спеціалістів: {result['specialists']}")
        print(f"  Блогів (цілителі): {result['blogs']}")
        print(f"  Портфоліо (художники/дизайнери): {result['portfolio_items']}")
        print()
        print("  Сід завершено успішно.")
    except Exception as e:
        print(f"  Помилка сіду: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    asyncio.run(main())
