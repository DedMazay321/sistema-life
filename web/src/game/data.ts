import questsJson from './quests.json'

export type Category = 'body' | 'mind' | 'discipline' | 'recovery' | 'social' | 'finance' | 'environment' | 'creativity'
export type Attribute = 'strength' | 'intellect' | 'discipline' | 'energy' | 'empathy' | 'awareness'
export type Difficulty = 'light' | 'standard' | 'challenge'

export interface Quest {
  id: string
  title: string
  category: Category
  description: string
  xp: number
  minLevel: number
  base: number
  step: number
  maxTarget: number
}

export interface CustomTask {
  id: string
  title: string
  description: string
  category: Category
  xp: number
  weekdays: number[]
}

export interface JournalEntry { note: string }

export interface PlayerState {
  version: 4
  totalXp: number
  attributes: Record<Attribute, number>
  history: Record<string, string[]>
  dailySets: Record<string, string[]>
  rewards: Record<string, Record<string, number>>
  unlockedAchievements: string[]
  difficulty: Difficulty
  customTasks: CustomTask[]
  journal: Record<string, Record<string, JournalEntry>>
  weeklyGoals: Record<string, string>
  weeklyDone: string[]
  restDays: string[]
  completedChains: string[]
  reminderEnabled: boolean
  reminderMinute: number
  pinHash: string
  playerName: string
  createdAt: string
}

export const QUESTS = questsJson as Quest[]
export const QUEST_BY_ID = Object.fromEntries(QUESTS.map((quest) => [quest.id, quest])) as Record<string, Quest>
export const DAILY_QUEST_COUNT = 6
export const DAILY_BONUS_XP = 40
export const CATEGORIES: Record<Category, { label: string; short: string; color: string; attribute: Attribute }> = {
  body: { label: 'Тело', short: 'ТЕЛО', color: '#5de4ee', attribute: 'strength' },
  mind: { label: 'Разум', short: 'РАЗУМ', color: '#a88bfa', attribute: 'intellect' },
  discipline: { label: 'Дисциплина', short: 'ДИСЦИПЛИНА', color: '#6f9fff', attribute: 'discipline' },
  recovery: { label: 'Восстановление', short: 'РЕСУРС', color: '#74d9a5', attribute: 'energy' },
  social: { label: 'Отношения', short: 'ОТНОШЕНИЯ', color: '#f09eae', attribute: 'empathy' },
  finance: { label: 'Финансы', short: 'ФИНАНСЫ', color: '#e9c778', attribute: 'awareness' },
  environment: { label: 'Порядок', short: 'ПОРЯДОК', color: '#8db9cf', attribute: 'discipline' },
  creativity: { label: 'Творчество', short: 'ТВОРЧЕСТВО', color: '#d6a2f1', attribute: 'intellect' },
}
export const ATTRIBUTES: Record<Attribute, string> = {
  strength: 'Сила', intellect: 'Интеллект', discipline: 'Дисциплина',
  energy: 'Энергия', empathy: 'Эмпатия', awareness: 'Осознанность',
}
export const TIER_NAMES = ['БРОНЗА', 'СЕРЕБРО', 'ЗОЛОТО', 'ПЛАТИНА']
export const TIER_COLORS = ['#bc8868', '#a9b7c9', '#f0c35c', '#8ee8ff']

export interface Achievement {
  id: string
  title: string
  description: string
  metric: string
  thresholds: number[]
  secret?: boolean
}
export const ACHIEVEMENTS: Achievement[] = [
  { id: 'path', title: 'Путь охотника', description: 'Выполняй любые задания', metric: 'completed', thresholds: [1, 10, 50, 200] },
  { id: 'streak', title: 'Нерушимая воля', description: 'Поддерживай серию полных дней', metric: 'streak', thresholds: [1, 3, 7, 30] },
  { id: 'level', title: 'Восхождение', description: 'Повышай уровень игрока', metric: 'level', thresholds: [2, 5, 10, 20] },
  { id: 'perfect', title: 'Безупречный день', description: 'Закрывай все шесть заданий дня', metric: 'perfect', thresholds: [1, 3, 10, 30] },
  { id: 'body', title: 'Предел тела', description: 'Выполняй задания направления «Тело»', metric: 'body', thresholds: [5, 25, 75, 200] },
  { id: 'mind', title: 'Архитектор разума', description: 'Выполняй задания направления «Разум»', metric: 'mind', thresholds: [5, 25, 75, 200] },
  { id: 'discipline', title: 'Железная дисциплина', description: 'Выполняй задания направления «Дисциплина»', metric: 'discipline', thresholds: [5, 25, 75, 200] },
  { id: 'recovery', title: 'Источник силы', description: 'Не забывай о восстановлении', metric: 'recovery', thresholds: [3, 15, 50, 150] },
  { id: 'social', title: 'Связь миров', description: 'Развивай отношения с людьми', metric: 'social', thresholds: [1, 10, 30, 75] },
  { id: 'finance', title: 'Хранитель ресурсов', description: 'Выполняй финансовые задания', metric: 'finance', thresholds: [1, 10, 30, 75] },
  { id: 'order', title: 'Властелин порядка', description: 'Наводи порядок вокруг себя', metric: 'environment', thresholds: [3, 15, 50, 150] },
  { id: 'creativity', title: 'Создатель', description: 'Выполняй творческие задания', metric: 'creativity', thresholds: [1, 10, 30, 75] },
  { id: 'xp', title: 'Накопленная мощь', description: 'Получай опыт за реальные действия', metric: 'xp', thresholds: [100, 500, 2000, 7500] },
  { id: 'journal', title: 'Летописец', description: 'Секретная награда за записи результатов', metric: 'journal', thresholds: [1, 7, 30, 100], secret: true },
  { id: 'boss', title: 'Победитель недели', description: 'Секретная награда за недельные цели', metric: 'boss', thresholds: [1, 4, 12, 52], secret: true },
  { id: 'personal', title: 'Свой путь', description: 'Секретная награда за личные задания', metric: 'custom', thresholds: [1, 10, 30, 100], secret: true },
  { id: 'variety', title: 'Мастер всех стихий', description: 'Секретная награда за разные направления', metric: 'variety', thresholds: [2, 4, 6, 8], secret: true },
  { id: 'chains', title: 'Неразрывная цепь', description: 'Секретная награда за цепочки', metric: 'chains', thresholds: [1, 2, 4, 8], secret: true },
]

export interface QuestChain { id: string; title: string; category: Category; days: number; reward: number }
export const CHAINS: QuestChain[] = [
  { id: 'body7', title: 'Семь дней движения', category: 'body', days: 7, reward: 100 },
  { id: 'mind7', title: 'Неделя знаний', category: 'mind', days: 7, reward: 100 },
  { id: 'discipline14', title: 'Две недели воли', category: 'discipline', days: 14, reward: 180 },
  { id: 'recovery7', title: 'Семь дней ресурса', category: 'recovery', days: 7, reward: 100 },
  { id: 'social7', title: 'Неделя связи', category: 'social', days: 7, reward: 100 },
  { id: 'finance7', title: 'Финансовое внимание', category: 'finance', days: 7, reward: 100 },
  { id: 'order7', title: 'Семь дней порядка', category: 'environment', days: 7, reward: 100 },
  { id: 'create7', title: 'Неделя созидания', category: 'creativity', days: 7, reward: 100 },
]
