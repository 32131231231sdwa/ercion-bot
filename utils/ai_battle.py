import os
import random
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

RANDOM_OUTCOMES = [
    "победа сил А — враг разгромлен и обращён в бегство, поле битвы осталось за наступающими",
    "победа сил Б — силы А не смогли устоять против натиска и отступили с потерями",
    "тяжёлая победа сил А — обе стороны понесли серьёзные потери, но силы А удержали позиции",
    "тяжёлая победа сил Б — сражение длилось несколько часов, силы Б взяли верх ценой большой крови",
    "ничья — сражение зашло в тупик, обе стороны отступили для перегруппировки",
    "силы А отступают в порядке — тактическое отступление позволило сохранить основной костяк войска",
    "прорыв флангов сил Б — хитрый манёвр окружения решил исход битвы не в пользу сил А",
    "засада — силы Б устроили засаду в лесу, силы А оказались в ловушке и понесли тяжелейшие потери",
    "переговоры — в разгар сражения стороны решили заключить временное перемирие",
    "вмешательство третьей стороны — неизвестные силы атаковали обе армии, изменив ход битвы",
]


async def generate_battle_outcomes_ai(force_a: str, force_b: str) -> Optional[str]:
    try:
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL", "")
        if not openai_key and not base_url:
            return None

        try:
            from openai import AsyncOpenAI
        except ImportError:
            return None

        client = AsyncOpenAI(
            api_key=openai_key or "dummy",
            base_url=base_url if base_url else None,
        )

        prompt = (
            f"Ты — летописец фэнтезийного мира Эрцион. "
            f"Опиши ровно 10 возможных вариантов исхода битвы между «{force_a}» и «{force_b}». "
            f"Пронумеруй варианты 1-10. Каждый вариант — одно-два предложения в эпическом стиле. "
            f"Затем скажи: «Произошедший исход: [номер]» и опиши его подробнее."
        )

        response = await client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=1024,
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.warning(f"AI battle failed: {e}")
        return None


def generate_battle_random(force_a: str, force_b: str) -> str:
    outcomes = []
    for i, outcome in enumerate(RANDOM_OUTCOMES, 1):
        outcome_text = outcome.replace("сил А", f"«{force_a}»").replace("сил Б", f"«{force_b}»")
        outcomes.append(f"{i}. {outcome_text.capitalize()}")

    chosen_idx = random.randint(0, len(RANDOM_OUTCOMES) - 1)
    chosen = RANDOM_OUTCOMES[chosen_idx].replace("сил А", f"«{force_a}»").replace("сил Б", f"«{force_b}»")

    text = f"⚔️ <b>Битва: {force_a} vs {force_b}</b>\n\n"
    text += "📜 <b>10 возможных исходов:</b>\n\n"
    for line in outcomes:
        text += f"{line}\n"
    text += f"\n⚡ <b>Произошедший исход ({chosen_idx + 1}):</b>\n{chosen.capitalize()}."
    return text
