from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import random
from typing import Iterable

from .quest_expansion import EXTRA_QUEST_DATA


DAILY_QUEST_COUNT = 6
DAILY_BONUS_XP = 40
BALANCE_BONUS_XP = 20
TIER_NAMES = ("БРОНЗА", "СЕРЕБРО", "ЗОЛОТО", "ПЛАТИНА")
TIER_COLORS = ("#B77B52", "#A9B7C9", "#F0C35C", "#8EE8FF")
CATEGORY_LABELS = {
    "body": "ТЕЛО",
    "mind": "РАЗУМ",
    "discipline": "ДИСЦИПЛИНА",
    "recovery": "ВОССТАНОВЛЕНИЕ",
    "social": "ОТНОШЕНИЯ",
    "finance": "ФИНАНСЫ",
    "environment": "ПОРЯДОК",
    "creativity": "ТВОРЧЕСТВО",
}
ATTRIBUTE_LABELS = {
    "strength": "Сила",
    "intellect": "Интеллект",
    "discipline": "Дисциплина",
    "energy": "Энергия",
    "empathy": "Эмпатия",
    "awareness": "Осознанность",
}
CATEGORY_ATTRIBUTES = {
    "body": "strength",
    "mind": "intellect",
    "discipline": "discipline",
    "recovery": "energy",
    "social": "empathy",
    "finance": "awareness",
    "environment": "discipline",
    "creativity": "intellect",
}


def _valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _weekly_tasks_from(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): [str(task) for task in value if str(task).strip()][:12]
        for key, value in raw.items()
        if isinstance(value, list)
    }


@dataclass(frozen=True)
class Quest:
    id: str
    title: str
    category: str
    description: str
    xp: int
    min_level: int = 1
    base: int = 0
    step: int = 0
    max_target: int = 0

    @property
    def attribute(self) -> str:
        return CATEGORY_ATTRIBUTES[self.category]

    def target(self, level: int, difficulty: str = "standard") -> int:
        if not self.base:
            return 0
        normal = min(self.max_target, self.base + self.step * (max(1, level) - 1))
        if difficulty == "light":
            return max(1, int(normal * 0.75))
        if difficulty == "challenge":
            return max(normal, int(normal * 1.25))
        return normal

    def scaled_description(self, level: int, difficulty: str = "standard") -> str:
        return self.description.format(target=self.target(level, difficulty))

    def reward(self, level: int) -> int:
        return self.xp + min(20, (max(1, level) - 1) * 2)


def q(
    id: str,
    title: str,
    category: str,
    description: str,
    xp: int,
    min_level: int = 1,
    base: int = 0,
    step: int = 0,
    max_target: int = 0,
) -> Quest:
    return Quest(id, title, category, description, xp, min_level, base, step, max_target)


QUESTS: tuple[Quest, ...] = (
    # Каждое описание содержит действие и наблюдаемый критерий завершения.
    q("pushups", "Отжимания: 3 подхода", "body", "Сделай {target} отжиманий суммарно за 3 подхода; отдых между ними — 60 секунд. Подойдёт вариант от стены или с колен.", 30, base=8, step=2, max_target=50),
    q("squats", "Приседания: техника", "body", "Сделай {target} приседаний суммарно за 3 подхода. Стопы на ширине плеч, спина нейтральная; запиши количество в каждом подходе.", 30, base=12, step=3, max_target=80),
    q("plank", "Планка: точное время", "body", "Набери {target} секунд планки суммарно за 2–4 подхода. Засеки время и заверши подход до потери техники.", 25, base=20, step=5, max_target=180),
    q("walk", "Пеший маршрут", "body", "Пройди {target} минут по таймеру в комфортном темпе. Телефон в кармане, последние 2 минуты — замедление.", 25, base=15, step=2, max_target=60),
    q("stretch", "Растяжка: 4 зоны", "body", "За {target} минут проработай шею, грудной отдел, бёдра и голени: минимум 30 секунд на каждую зону, без боли.", 20, base=8, step=1, max_target=25),
    q("mobility", "Суставная разминка", "body", "За {target} минут выполни по 8 плавных кругов плечами, тазом и стопами в каждую сторону, затем 10 медленных наклонов.", 20, base=8, step=1, max_target=25),
    q("stairs", "Лестница вместо лифта", "body", "Идти по лестнице {target} минут с пульсом, позволяющим говорить. Если лестницы нет — столько же минут быстрой ходьбы.", 25, 2, 3, 1, 15),
    q("workout", "Тренировка по схеме", "body", "5 минут разминки, затем {target} минут круговой тренировки и 3 минуты заминки. Выбери 4 упражнения и запиши завершённые круги.", 45, 3, 20, 2, 60),
    q("posture", "Перерывы на осанку", "body", "Сделай {target} перерывов по 60 секунд: встань, сведи лопатки 10 раз и потянись вверх. Поставь напоминания заранее.", 20, base=3, step=1, max_target=8),
    q("steps", "Шаговый норматив", "body", "Добавь {target} шагов к обычному дневному минимуму. Отметь результат шагомером до завершения дня.", 35, 4, 2000, 500, 8000),

    q("read", "Чтение с результатом", "mind", "Читай одну книгу {target} минут без переключений, затем запиши главную мысль в 3 предложениях и один применимый вывод.", 25, base=15, step=2, max_target=45),
    q("course", "Один урок до конца", "mind", "Заверши один урок курса и занимайся не менее {target} минут. Сделай конспект из 5 пунктов и выполни упражнение урока.", 30, base=20, step=2, max_target=60),
    q("language", "Язык: слова и фразы", "mind", "Занимайся {target} минут: выучи 10 новых слов, составь с 5 из них предложения и прочитай их вслух.", 25, base=15, step=2, max_target=45),
    q("notes", "Конспект по схеме", "mind", "Запиши {target} отдельные идеи из сегодняшнего обучения. К каждой добавь пример или вопрос — не копируй текст дословно.", 20, base=3, step=1, max_target=8),
    q("recall", "Активное вспоминание", "mind", "Закрой материалы и запиши {target} фактов по памяти. Затем сверься с источником и исправь ошибки другим цветом.", 25, 2, 3, 1, 10),
    q("deep_learning", "Одна сложная тема", "mind", "Поставь таймер на {target} минут и изучи один подраздел. После паузы напиши определение темы и реши одну задачу без подсказки.", 40, 3, 25, 3, 60),
    q("teach", "Объяснение без терминов", "mind", "Выбери одну идею и объясни её в 5 предложениях без профессионального жаргона. Последним предложением приведи бытовой пример.", 25),
    q("question", "Три вопроса к цели", "mind", "Запиши 3 вопроса, которые мешают двигаться к текущей цели. Найди ответ на один и запиши следующий конкретный шаг.", 15),
    q("review", "Повторение заметок", "mind", "Открой {target} старые заметки, отметь ключевую фразу в каждой и добавь одну новую связь между ними.", 25, 2, 3, 1, 10),
    q("focus_read", "Две страницы внимательно", "mind", "Прочитай 2 страницы сложного текста, выпиши 3 незнакомых понятия и напиши резюме длиной до 80 слов.", 25, 4),

    q("plan_day", "План на три результата", "discipline", "Запиши {target} результата дня, назначь каждому время и подчеркни первый шаг. Заверши план до начала работы.", 20, base=3, step=0, max_target=3),
    q("important_first", "Главная задача первой", "discipline", "До почты и мессенджеров включи таймер на {target} минут и делай только задачу №1. Отметь измеримый результат сессии.", 35, base=20, step=3, max_target=60),
    q("no_feed", "Блок без ленты", "discipline", "Включи блокировку соцсетей и новостей на {target} минут. В это время не открывай их ни на одном устройстве.", 25, base=30, step=5, max_target=120),
    q("make_bed", "Порядок за 2 минуты", "discipline", "Сразу после подъёма заправь кровать, расправь покрывало и убери посторонние предметы с неё. Готово — когда поверхность пустая и ровная.", 10),
    q("start_on_time", "Старт по расписанию", "discipline", "Выбери задачу и точное время. В назначенную минуту запусти 15‑минутный таймер и начни без подготовительных ритуалов.", 25, 2),
    q("digital_sunset", "Телефон вне спальни", "discipline", "За {target} минут до сна поставь телефон на зарядку вне спальни, закрой ноутбук и включи будильник заранее.", 30, 2, 30, 5, 90),
    q("small_promise", "Обещание до 10 минут", "discipline", "Утром запиши одно действие до 10 минут и точное время. Выполни его и отметь время завершения рядом с записью.", 20),
    q("procrastination", "Разбить откладывание", "discipline", "Открой отложенное дело, выпиши следующий физический шаг и работай {target} минут. Заверши хотя бы этот шаг.", 30, base=10, step=2, max_target=30),
    q("inbox", "Входящие: решение", "discipline", "Обработай {target} входящих элементов: для каждого выбери «удалить», «ответить», «делегировать» или «назначить срок».", 20, 2, 5, 2, 20),
    q("weekly_review", "Итоги в трёх строках", "discipline", "Перед сном запиши по одному пункту: результат дня, причина ошибки и первое действие завтра. Каждый пункт — не длиннее 20 слов.", 25),

    q("breathing", "Дыхание 4–6", "recovery", "Дыши {target} минут по схеме: вдох 4 секунды, выдох 6. Сядь удобно, поставь таймер и не задерживай дыхание.", 20, base=5, step=1, max_target=15),
    q("nature", "Прогулка без экрана", "recovery", "Проведи {target} минут на улице без наушников и прокрутки экрана. Назови про себя 5 деталей вокруг, которые заметил.", 25, base=20, step=2, max_target=60),
    q("screen_break", "Правило для глаз", "recovery", "Сделай {target} перерывов по 60 секунд примерно каждые 45 минут: закрой экран, посмотри вдаль и медленно моргай 10 раз.", 20, base=3, step=1, max_target=8),
    q("meditation", "Медитация по таймеру", "recovery", "Медитируй {target} минут: считай выдохи от 1 до 10 и начинай заново при отвлечении. Телефон переведи в режим полёта.", 25, 2, 5, 1, 20),
    q("hobby_rest", "Отдых по расписанию", "recovery", "Выбери одно спокойное занятие, поставь таймер на {target} минут и не фотографируй результат. Заверши без проверки сообщений.", 20, base=20, step=2, max_target=45),
    q("evening_stretch", "Вечерний комплекс", "recovery", "За {target} минут сделай 5 движений по 30 секунд: наклон, поза ребёнка, скручивание, растяжка бедра и грудного отдела.", 20, base=8, step=1, max_target=20),
    q("gratitude", "Благодарность с причиной", "recovery", "Запиши {target} события дня по формуле «Я благодарен за…, потому что…». Каждая запись — одно полное предложение.", 15, base=3, step=0, max_target=3),
    q("sleep_ready", "Ритуал перед сном", "recovery", "За 30 минут до сна подготовь одежду, поставь будильник и убери экран. Ляг в выбранное время с завершёнными тремя шагами.", 30, 3),

    q("message_friend", "Сообщение другу", "social", "Напиши другу 3 предложения: конкретное воспоминание, вопрос о его делах и предложение созвониться или встретиться.", 15),
    q("call_family", "Звонок близкому", "social", "Говори с близким {target} минут. Задай минимум 2 открытых вопроса и не проверяй экран во время ответов.", 25, base=10, step=2, max_target=30),
    q("help", "Десять минут помощи", "social", "Спроси конкретного человека: «Чем могу помочь за 10 минут?» Выполни одну названную задачу или предложи свою конкретную.", 25),
    q("compliment", "Конкретный комплимент", "social", "Назови человеку одно его действие и его положительный эффект. Не ограничивайся общей фразой «молодец».", 15),
    q("conversation", "Разговор без телефона", "social", "Говори {target} минут, убрав телефон. Задай 3 открытых вопроса и кратко перефразируй один ответ, чтобы проверить понимание.", 30, 2, 10, 2, 30),
    q("boundary", "Отказ по формуле", "social", "На одну лишнюю просьбу ответь по схеме: «Спасибо за предложение — мне это не подходит — могу предложить…». Не добавляй длинных оправданий.", 25, 4),

    q("track_expenses", "Каждая трата записана", "finance", "Занеси каждую трату дня в таблицу: сумма, категория, необходимость «да/нет». Проверь, что в списке нет пропусков по счёту.", 20),
    q("pause_purchase", "Пауза перед покупкой", "finance", "Добавь необязательный товар в список ожидания на {target} часа: запиши цену, причину покупки и дату повторного решения. Сейчас не покупай.", 20, base=24, step=0, max_target=24),
    q("budget", "Сверка бюджета", "finance", "За {target} минут сравни план и факт по 3 категориям расходов. Запиши отклонение и одно действие по каждой категории.", 30, 2, 10, 2, 30),
    q("save", "Перевод в резерв", "finance", "Переведи заранее выбранную посильную сумму на отдельный накопительный счёт и запиши новый остаток резерва.", 30, 2),
    q("compare", "Сравнение трёх вариантов", "finance", "Составь таблицу из {target} вариантов покупки: цена, гарантия, 2 ключевые характеристики. Выбери вариант письменно или отложи решение.", 20, base=3, step=0, max_target=3),
    q("finance_learn", "Финансовый конспект", "finance", "Изучай одну тему личных финансов {target} минут по надёжному источнику. Запиши 5 тезисов и один термин с собственным определением.", 25, 3, 15, 2, 40),

    q("desk", "Рабочий стол: семь предметов", "environment", "Убери всё со стола, протри поверхность и верни не больше 7 рабочих предметов. Каждому назначь постоянное место.", 20),
    q("room_reset", "Комната по четырём зонам", "environment", "Включи таймер на {target} минут и по очереди убери пол, рабочую поверхность, одежду и мусор. Заверши все 4 зоны.", 20, base=10, step=2, max_target=30),
    q("dishes", "Чистая раковина", "environment", "Сразу после еды вымой всю использованную посуду или загрузи машину. Заверши, когда раковина пустая, а поверхность протёрта.", 15),
    q("laundry", "Один полный цикл стирки", "environment", "Заверши одну стадию без новой кучи: собери и постирай, развесь или полностью сложи уже сухие вещи по местам.", 20),
    q("digital_clean", "Очистка десяти файлов", "environment", "Проверь {target} файлов или ярлыков: удали лишние, остальные перемести в тематические папки. В конце очисти корзину.", 20, 2, 10, 5, 40),
    q("declutter", "Пакет лишних вещей", "environment", "Выбери {target} предмета и положи их в пакет с подписями «выбросить», «отдать» или «продать». Назначь дату выноса пакета.", 25, 3, 3, 1, 10),

    q("write", "Черновик без правок", "creativity", "Напиши не менее {target} слов за одну сессию, не редактируя по ходу. После таймера выдели одну удачную фразу.", 25, base=100, step=25, max_target=400),
    q("draw", "Три быстрых наброска", "creativity", "Сделай 3 наброска одного предмета за {target} минут: с разных ракурсов и без стирания. Выбери один и отметь удачную деталь.", 25, base=15, step=2, max_target=40),
    q("music", "Упражнение и фрагмент", "creativity", "За {target} минут сыграй 5 минут упражнение в медленном темпе, затем один музыкальный фрагмент 3 раза без остановки.", 30, 2, 15, 2, 45),
    q("photo", "Один сюжет, три ракурса", "creativity", "Сфотографируй один объект с {target} разных ракурсов. Удали технические дубли и оставь по одному кадру на ракурс.", 20, base=3, step=1, max_target=10),
    q("ideas", "Пять идей и выбор", "creativity", "Запиши {target} идей для одного проекта без оценки. Затем обведи одну и допиши её первый шаг, который займёт меньше 15 минут.", 25, 2, 5, 1, 15),
    q("create", "Один готовый фрагмент", "creativity", "Работай над проектом {target} минут и заверши один маленький фрагмент: сцену, деталь, такт или макет. Сохрани результат отдельной версией.", 35, 3, 20, 3, 60),
)
QUESTS = QUESTS + tuple(Quest(*item) for item in EXTRA_QUEST_DATA)
QUEST_BY_ID = {quest.id: quest for quest in QUESTS}
assert len(QUEST_BY_ID) == len(QUESTS), "Quest identifiers must be unique"
assert len(QUESTS) == 248, "The expanded catalog must contain 248 quests"


@dataclass(frozen=True)
class CustomTask:
    id: str
    title: str
    description: str
    category: str = "discipline"
    xp: int = 20
    weekdays: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)

    def as_quest(self) -> Quest:
        return Quest(self.id, self.title, self.category, self.description, self.xp)


@dataclass(frozen=True)
class JournalEntry:
    note: str = ""
    photo: str = ""


@dataclass(frozen=True)
class DevelopmentArc:
    """A player-chosen area of growth measured by completed actions."""
    id: str
    title: str
    category: str
    target: int


@dataclass
class PlayerState:
    total_xp: int = 0
    attributes: dict[str, int] = field(default_factory=dict)
    history: dict[str, set[str]] = field(default_factory=dict)
    daily_sets: dict[str, list[str]] = field(default_factory=dict)
    rewards: dict[str, dict[str, int]] = field(default_factory=dict)
    unlocked_achievements: set[str] = field(default_factory=set)
    difficulty: str = "standard"
    custom_tasks: list[CustomTask] = field(default_factory=list)
    journal: dict[str, dict[str, JournalEntry]] = field(default_factory=dict)
    weekly_goals: dict[str, str] = field(default_factory=dict)
    weekly_done: set[str] = field(default_factory=set)
    rest_days: set[str] = field(default_factory=set)
    completed_chains: set[str] = field(default_factory=set)
    reminder_enabled: bool = False
    reminder_minute: int = 20 * 60
    pin_hash: str = ""
    arcs: list[DevelopmentArc] = field(default_factory=list)
    weekly_tasks: dict[str, list[str]] = field(default_factory=dict)
    weekly_task_done: set[str] = field(default_factory=set)
    balance_bonus_days: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "version": 3,
            "total_xp": self.total_xp,
            "attributes": self.attributes,
            "history": {day: sorted(ids) for day, ids in sorted(self.history.items())},
            "daily_sets": self.daily_sets,
            "rewards": self.rewards,
            "unlocked_achievements": sorted(self.unlocked_achievements),
            "difficulty": self.difficulty,
            "custom_tasks": [
                {"id": task.id, "title": task.title, "description": task.description,
                 "category": task.category, "xp": task.xp, "weekdays": list(task.weekdays)}
                for task in self.custom_tasks
            ],
            "journal": {day: {qid: vars(entry) for qid, entry in entries.items()} for day, entries in self.journal.items()},
            "weekly_goals": self.weekly_goals,
            "weekly_done": sorted(self.weekly_done),
            "rest_days": sorted(self.rest_days),
            "completed_chains": sorted(self.completed_chains),
            "reminder_enabled": self.reminder_enabled,
            "reminder_minute": self.reminder_minute,
            "pin_hash": self.pin_hash,
            "arcs": [vars(arc) for arc in self.arcs],
            "weekly_tasks": self.weekly_tasks,
            "weekly_task_done": sorted(self.weekly_task_done),
            "balance_bonus_days": sorted(self.balance_bonus_days),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerState":
        attributes = {key: max(0, int(data.get("attributes", {}).get(key, 0))) for key in ATTRIBUTE_LABELS}
        custom_tasks = []
        for item in data.get("custom_tasks", []):
            try:
                task = CustomTask(str(item["id"]), str(item["title"]), str(item["description"]),
                                  str(item.get("category", "discipline")), max(5, int(item.get("xp", 20))),
                                  tuple(int(day) for day in item.get("weekdays", range(1, 8)) if 1 <= int(day) <= 7))
                if task.id.startswith("custom:") and task.id not in QUEST_BY_ID and task.category in CATEGORY_LABELS:
                    custom_tasks.append(task)
            except (KeyError, TypeError, ValueError):
                continue
        custom_ids = {task.id for task in custom_tasks}
        arcs = []
        for item in data.get("arcs", []):
            try:
                arc = DevelopmentArc(str(item["id"]), str(item["title"]).strip(), str(item["category"]), int(item["target"]))
                if arc.id.startswith("arc:") and arc.title and arc.category in CATEGORY_LABELS and 3 <= arc.target <= 200:
                    arcs.append(arc)
            except (KeyError, TypeError, ValueError):
                continue
        history: dict[str, set[str]] = {}
        for day, ids in data.get("history", {}).items():
            try:
                date.fromisoformat(day)
                history[day] = {str(item) for item in ids if str(item) in QUEST_BY_ID or str(item) in custom_ids}
            except (ValueError, TypeError):
                continue
        daily_sets: dict[str, list[str]] = {}
        for day, ids in data.get("daily_sets", {}).items():
            try:
                date.fromisoformat(day)
            except (ValueError, TypeError):
                continue
            valid_ids = [str(item) for item in ids if str(item) in QUEST_BY_ID]
            if len(valid_ids) == DAILY_QUEST_COUNT and len(set(valid_ids)) == DAILY_QUEST_COUNT:
                daily_sets[day] = valid_ids
        rewards: dict[str, dict[str, int]] = {}
        for day, day_rewards in data.get("rewards", {}).items():
            if not isinstance(day_rewards, dict):
                continue
            rewards[day] = {str(qid): max(0, int(value)) for qid, value in day_rewards.items()
                            if str(qid) in QUEST_BY_ID or str(qid) in custom_ids}
        journal = {}
        for day, entries in data.get("journal", {}).items():
            try:
                date.fromisoformat(day)
                journal[day] = {str(qid): JournalEntry(str(value.get("note", "")), str(value.get("photo", "")))
                                for qid, value in entries.items() if isinstance(value, dict)}
            except (ValueError, TypeError, AttributeError):
                continue
        valid_keys = {f"{achievement.id}:{tier}" for achievement in ACHIEVEMENTS for tier in range(1, 5)}
        difficulty = data.get("difficulty", "standard")
        return cls(
            total_xp=max(0, int(data.get("total_xp", 0))), attributes=attributes, history=history,
            daily_sets=daily_sets, rewards=rewards,
            unlocked_achievements=set(data.get("unlocked_achievements", [])) & valid_keys,
            difficulty=difficulty if difficulty in {"light", "standard", "challenge"} else "standard",
            custom_tasks=custom_tasks, journal=journal,
            weekly_goals={str(k): str(v) for k, v in data.get("weekly_goals", {}).items()},
            weekly_done=set(data.get("weekly_done", [])), rest_days=set(data.get("rest_days", [])),
            completed_chains=set(data.get("completed_chains", [])),
            reminder_enabled=bool(data.get("reminder_enabled", False)),
            reminder_minute=max(0, min(1439, int(data.get("reminder_minute", 1200)))),
            pin_hash=str(data.get("pin_hash", "")),
            arcs=arcs,
            weekly_tasks=_weekly_tasks_from(data.get("weekly_tasks", {})),
            weekly_task_done={str(value) for value in data.get("weekly_task_done", [])},
            balance_bonus_days={str(value) for value in data.get("balance_bonus_days", [])
                                if _valid_iso_date(str(value))},
        )


@dataclass(frozen=True)
class LevelProgress:
    level: int
    current_xp: int
    needed_xp: int
    rank: str


def level_progress(total_xp: int) -> LevelProgress:
    remaining = max(0, total_xp)
    level = 1
    while True:
        needed = 100 + (level - 1) * 25
        if remaining < needed:
            rank = "S" if level >= 25 else "A" if level >= 17 else "B" if level >= 12 else "C" if level >= 8 else "D" if level >= 4 else "E"
            return LevelProgress(level, remaining, needed, rank)
        remaining -= needed
        level += 1


def daily_quests(day: date, level: int, previous_ids: Iterable[str] = ()) -> list[Quest]:
    rng = random.Random(f"sistema:{day.isoformat()}")
    core_categories = ["body", "mind", "discipline"]
    rotating = ["recovery", "social", "finance", "environment", "creativity"]
    rng.shuffle(rotating)
    categories = core_categories + rotating[: DAILY_QUEST_COUNT - len(core_categories)]
    excluded = set(previous_ids)
    selected: list[Quest] = []
    for category in categories:
        eligible = [quest for quest in QUESTS if quest.category == category and quest.min_level <= level]
        preferred = [quest for quest in eligible if quest.id not in excluded]
        choices = preferred or eligible
        rng.shuffle(choices)
        selected.append(choices[0])
    rng.shuffle(selected)
    return selected


def _stored_daily_quests(state: PlayerState, day: date) -> list[Quest]:
    ids = state.daily_sets.get(day.isoformat())
    if ids and len(ids) == DAILY_QUEST_COUNT:
        return [QUEST_BY_ID[quest_id] for quest_id in ids]
    return list(daily_quests(day, 1))


def get_daily_quests(state: PlayerState, day: date) -> list[Quest]:
    day_key = day.isoformat()
    existing = state.daily_sets.get(day_key)
    if existing and len(existing) == DAILY_QUEST_COUNT:
        return [QUEST_BY_ID[quest_id] for quest_id in existing]
    previous_ids = state.daily_sets.get((day - timedelta(days=1)).isoformat(), [])
    quests = daily_quests(day, level_progress(state.total_xp).level, previous_ids)
    state.daily_sets[day_key] = [quest.id for quest in quests]
    return quests


def is_day_complete(state: PlayerState, day: date) -> bool:
    if day.isoformat() in state.rest_days:
        return True
    daily_ids = {quest.id for quest in _stored_daily_quests(state, day)}
    return daily_ids.issubset(state.history.get(day.isoformat(), set()))


def completed_today(state: PlayerState, day: date) -> set[str]:
    daily_ids = {quest.id for quest in _stored_daily_quests(state, day)}
    return state.history.get(day.isoformat(), set()) & daily_ids


def custom_due(state: PlayerState, day: date) -> list[CustomTask]:
    return [task for task in state.custom_tasks if day.isoweekday() in task.weekdays]


def adjusted_reward(state: PlayerState, quest: Quest) -> int:
    normal = quest.reward(level_progress(state.total_xp).level)
    if state.difficulty == "light":
        return max(5, int(normal * 0.8))
    if state.difficulty == "challenge":
        return int(normal * 1.25)
    return normal


def toggle_quest(state: PlayerState, quest: Quest, day: date) -> tuple[bool, bool, list[tuple["Achievement", int]]]:
    day_key = day.isoformat()
    get_daily_quests(state, day)
    old_level = level_progress(state.total_xp).level
    today = set(state.history.get(day_key, set()))
    was_complete = is_day_complete(state, day)
    was_balanced = has_daily_balance(state, day)
    completing = quest.id not in today
    reward = adjusted_reward(state, quest)

    if completing:
        today.add(quest.id)
        state.total_xp += reward
        state.attributes[quest.attribute] = state.attributes.get(quest.attribute, 0) + 1
        state.rewards.setdefault(day_key, {})[quest.id] = reward
    else:
        if was_complete and day_key not in state.rest_days:
            state.total_xp = max(0, state.total_xp - DAILY_BONUS_XP)
        today.discard(quest.id)
        awarded = state.rewards.get(day_key, {}).get(quest.id, reward)
        state.total_xp = max(0, state.total_xp - awarded)
        state.attributes[quest.attribute] = max(0, state.attributes.get(quest.attribute, 0) - 1)
        state.rewards.get(day_key, {}).pop(quest.id, None)

    state.history[day_key] = today
    now_complete = is_day_complete(state, day)
    if completing and not was_complete and now_complete:
        state.total_xp += DAILY_BONUS_XP
    now_balanced = has_daily_balance(state, day)
    if now_balanced and not was_balanced and day_key not in state.balance_bonus_days:
        state.balance_bonus_days.add(day_key)
        state.total_xp += BALANCE_BONUS_XP
    elif was_balanced and not now_balanced and day_key in state.balance_bonus_days:
        state.balance_bonus_days.remove(day_key)
        state.total_xp = max(0, state.total_xp - BALANCE_BONUS_XP)
    apply_chains(state, day)
    new_unlocks = sync_achievements(state, day)
    leveled_up = level_progress(state.total_xp).level > old_level
    return completing, leveled_up, new_unlocks


def week_key(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week}"


def daily_categories(state: PlayerState, day: date) -> set[str]:
    quests = all_quests(state)
    return {quests[quest_id].category for quest_id in state.history.get(day.isoformat(), set()) if quest_id in quests}


def has_daily_balance(state: PlayerState, day: date) -> bool:
    """Four different directions in one day earns a small sustainable-progress bonus."""
    return len(daily_categories(state, day)) >= 4


def toggle_weekly_task(state: PlayerState, day: date, index: int) -> bool:
    key = week_key(day)
    if index not in range(len(state.weekly_tasks.get(key, []))):
        return False
    marker = f"{key}:{index}"
    if marker in state.weekly_task_done:
        state.weekly_task_done.remove(marker)
        return False
    state.weekly_task_done.add(marker)
    return True


def arc_progress(state: PlayerState, arc: DevelopmentArc) -> int:
    return min(arc.target, category_completed(state, arc.category))


def toggle_weekly_done(state: PlayerState, day: date) -> bool:
    key = week_key(day)
    if not state.weekly_goals.get(key, "").strip():
        return False
    if key in state.weekly_done:
        state.weekly_done.remove(key)
        state.total_xp = max(0, state.total_xp - 100)
        return False
    state.weekly_done.add(key)
    state.total_xp += 100
    return True


def streak(state: PlayerState, today: date) -> int:
    cursor = today
    count = 0
    while is_day_complete(state, cursor):
        count += 1
        cursor -= timedelta(days=1)
    return count


def perfect_days(state: PlayerState, today: date) -> int:
    count = 0
    for day_key in state.history:
        try:
            parsed = date.fromisoformat(day_key)
        except ValueError:
            continue
        if parsed <= today and day_key not in state.rest_days and is_day_complete(state, parsed):
            count += 1
    return count


@dataclass(frozen=True)
class Achievement:
    id: str
    title: str
    description: str
    metric: str
    thresholds: tuple[int, int, int, int]
    secret: bool = False


ACHIEVEMENTS: tuple[Achievement, ...] = (
    Achievement("path", "Путь охотника", "Выполняй любые задания", "completed", (1, 10, 50, 200)),
    Achievement("streak", "Нерушимая воля", "Поддерживай серию полных дней", "streak", (1, 3, 7, 30)),
    Achievement("level", "Восхождение", "Повышай уровень игрока", "level", (2, 5, 10, 20)),
    Achievement("perfect", "Безупречный день", "Закрывай все шесть заданий дня", "perfect", (1, 3, 10, 30)),
    Achievement("body", "Предел тела", "Выполняй задания направления «Тело»", "body", (5, 25, 75, 200)),
    Achievement("mind", "Архитектор разума", "Выполняй задания направления «Разум»", "mind", (5, 25, 75, 200)),
    Achievement("discipline", "Железная дисциплина", "Выполняй задания направления «Дисциплина»", "discipline", (5, 25, 75, 200)),
    Achievement("recovery", "Источник силы", "Не забывай о восстановлении", "recovery", (3, 15, 50, 150)),
    Achievement("social", "Связь миров", "Развивай отношения с людьми", "social", (1, 10, 30, 75)),
    Achievement("finance", "Хранитель ресурсов", "Выполняй финансовые задания", "finance", (1, 10, 30, 75)),
    Achievement("order", "Властелин порядка", "Наводи порядок вокруг себя", "environment", (3, 15, 50, 150)),
    Achievement("creativity", "Создатель", "Выполняй творческие задания", "creativity", (1, 10, 30, 75)),
    Achievement("xp", "Накопленная мощь", "Получай опыт за реальные действия", "xp", (100, 500, 2000, 7500)),
    Achievement("journal", "Летописец", "Секретная награда за записи результатов", "journal", (1, 7, 30, 100), True),
    Achievement("boss", "Победитель недели", "Секретная награда за недельные цели", "boss", (1, 4, 12, 52), True),
    Achievement("personal", "Свой путь", "Секретная награда за личные задания", "custom", (1, 10, 30, 100), True),
    Achievement("variety", "Мастер всех стихий", "Секретная награда за разные направления", "variety", (2, 4, 6, 8), True),
    Achievement("chains", "Неразрывная цепь", "Секретная награда за цепочки", "chains", (1, 2, 4, 8), True),
)


@dataclass(frozen=True)
class QuestChain:
    id: str
    title: str
    category: str
    days: int
    reward: int


CHAINS = (
    QuestChain("body7", "Семь дней движения", "body", 7, 100),
    QuestChain("mind7", "Неделя знаний", "mind", 7, 100),
    QuestChain("discipline14", "Две недели воли", "discipline", 14, 180),
    QuestChain("recovery7", "Семь дней ресурса", "recovery", 7, 100),
    QuestChain("social7", "Неделя связи", "social", 7, 100),
    QuestChain("finance7", "Финансовое внимание", "finance", 7, 100),
    QuestChain("order7", "Семь дней порядка", "environment", 7, 100),
    QuestChain("create7", "Неделя созидания", "creativity", 7, 100),
)


def all_quests(state: PlayerState) -> dict[str, Quest]:
    return QUEST_BY_ID | {task.id: task.as_quest() for task in state.custom_tasks}


def category_completed(state: PlayerState, category: str) -> int:
    quests = all_quests(state)
    return sum(1 for completed in state.history.values() for quest_id in completed
               if quest_id in quests and quests[quest_id].category == category)


def category_completed_on(state: PlayerState, category: str, day: date) -> int:
    quests = all_quests(state)
    return sum(1 for quest_id in state.history.get(day.isoformat(), set())
               if quest_id in quests and quests[quest_id].category == category)


def metric_value(state: PlayerState, metric: str, today: date) -> int:
    if metric == "completed":
        return sum(len(ids) for ids in state.history.values())
    if metric == "streak":
        return streak(state, today)
    if metric == "level":
        return level_progress(state.total_xp).level
    if metric == "perfect":
        return perfect_days(state, today)
    if metric == "xp":
        return state.total_xp
    if metric == "journal":
        return sum(len(entries) for entries in state.journal.values())
    if metric == "boss":
        return len(state.weekly_done)
    if metric == "custom":
        ids = {task.id for task in state.custom_tasks}
        return sum(1 for completed in state.history.values() for qid in completed if qid in ids)
    if metric == "variety":
        quests = all_quests(state)
        return len({quests[qid].category for completed in state.history.values() for qid in completed if qid in quests})
    if metric == "chains":
        return len(state.completed_chains)
    return category_completed(state, metric)


def sync_achievements(state: PlayerState, today: date) -> list[tuple[Achievement, int]]:
    unlocked: list[tuple[Achievement, int]] = []
    for achievement in ACHIEVEMENTS:
        value = metric_value(state, achievement.metric, today)
        for tier, threshold in enumerate(achievement.thresholds, start=1):
            key = f"{achievement.id}:{tier}"
            if value >= threshold and key not in state.unlocked_achievements:
                state.unlocked_achievements.add(key)
                unlocked.append((achievement, tier))
    return unlocked


def achievement_tier(state: PlayerState, achievement: Achievement) -> int:
    return sum(1 for tier in range(1, 5) if f"{achievement.id}:{tier}" in state.unlocked_achievements)


def chain_progress(state: PlayerState, chain: QuestChain, today: date) -> int:
    count = 0
    cursor = today
    while count < chain.days and category_completed_on(state, chain.category, cursor):
        count += 1
        cursor -= timedelta(days=1)
    return count


def apply_chains(state: PlayerState, today: date) -> None:
    for chain in CHAINS:
        if chain.id not in state.completed_chains and chain_progress(state, chain, today) >= chain.days:
            state.completed_chains.add(chain.id)
            state.total_xp += chain.reward


def weekly_recommendation(state: PlayerState, today: date) -> str:
    counts = {category: sum(category_completed_on(state, category, today - timedelta(days=offset)) for offset in range(7))
              for category in CATEGORY_LABELS}
    weakest = min(counts, key=counts.get)
    return f"На следующей неделе добавь внимание направлению «{CATEGORY_LABELS[weakest]}»: сейчас здесь меньше всего действий."
