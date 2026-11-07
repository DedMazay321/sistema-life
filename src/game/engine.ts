import {
  ACHIEVEMENTS, ATTRIBUTES, CATEGORIES, CHAINS, DAILY_BONUS_XP, DAILY_QUEST_COUNT,
  QUESTS, QUEST_BY_ID,
} from './data'
import type { Achievement, Attribute, CustomTask, Difficulty, PlayerState, Quest } from './data'

export const STORAGE_KEY = 'sistema.web.player.v4'
export const todayKey = () => dateKey(new Date())
export function dateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
export function parseDay(key: string): Date {
  const [year, month, day] = key.split('-').map(Number)
  return new Date(year, month - 1, day, 12)
}
export function shiftDay(key: string, amount: number): string {
  const date = parseDay(key)
  date.setDate(date.getDate() + amount)
  return dateKey(date)
}
export function weekKey(key = todayKey()): string {
  const date = parseDay(key)
  const day = date.getDay() || 7
  date.setDate(date.getDate() + 4 - day)
  const yearStart = new Date(date.getFullYear(), 0, 1)
  const week = Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
  return `${date.getFullYear()}-W${week}`
}
export function emptyAttributes(): Record<Attribute, number> {
  return { strength: 0, intellect: 0, discipline: 0, energy: 0, empathy: 0, awareness: 0 }
}
export function createInitialState(): PlayerState {
  const state: PlayerState = {
    version: 4, totalXp: 0, attributes: emptyAttributes(), history: {}, dailySets: {}, rewards: {},
    unlockedAchievements: [], difficulty: 'standard', customTasks: [], journal: {}, weeklyGoals: {},
    weeklyDone: [], restDays: [], completedChains: [], reminderEnabled: false, reminderMinute: 1200,
    pinHash: '', playerName: 'Игрок', createdAt: todayKey(),
  }
  ensureDaily(state, todayKey())
  return state
}
function integer(value: unknown, fallback = 0): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.max(0, Math.floor(parsed)) : fallback
}
export function normalizeState(input: unknown): PlayerState {
  if (!input || typeof input !== 'object') throw new Error('Некорректный файл сохранения')
  const raw = input as Partial<PlayerState>
  const base = createInitialState()
  const customTasks: CustomTask[] = Array.isArray(raw.customTasks) ? raw.customTasks.flatMap((item) => {
    if (!item || typeof item !== 'object' || !String(item.id).startsWith('custom:')) return []
    const category = item.category in CATEGORIES ? item.category : 'discipline'
    const title = String(item.title ?? '').trim().slice(0, 100)
    if (!title) return []
    return [{
      id: String(item.id), title, description: String(item.description ?? '').trim().slice(0, 1000),
      category, xp: Math.min(100, Math.max(5, integer(item.xp, 20))),
      weekdays: Array.isArray(item.weekdays) ? [...new Set(item.weekdays.filter((day) => Number.isInteger(day) && day >= 1 && day <= 7))] : [1, 2, 3, 4, 5, 6, 7],
    }]
  }) : []
  const customIds = new Set(customTasks.map((task) => task.id))
  const validQuest = (id: unknown) => typeof id === 'string' && (id in QUEST_BY_ID || customIds.has(id))
  const history: PlayerState['history'] = {}
  if (raw.history && typeof raw.history === 'object') {
    Object.entries(raw.history).forEach(([day, ids]) => {
      if (/^\d{4}-\d{2}-\d{2}$/.test(day) && Array.isArray(ids)) history[day] = [...new Set(ids.filter(validQuest))]
    })
  }
  const dailySets: PlayerState['dailySets'] = {}
  if (raw.dailySets && typeof raw.dailySets === 'object') {
    Object.entries(raw.dailySets).forEach(([day, ids]) => {
      if (Array.isArray(ids) && ids.length === DAILY_QUEST_COUNT && ids.every((id) => typeof id === 'string' && id in QUEST_BY_ID)) dailySets[day] = [...new Set(ids)]
      if (dailySets[day]?.length !== DAILY_QUEST_COUNT) delete dailySets[day]
    })
  }
  const rewards: PlayerState['rewards'] = {}
  if (raw.rewards && typeof raw.rewards === 'object') {
    Object.entries(raw.rewards).forEach(([day, values]) => {
      if (!values || typeof values !== 'object') return
      rewards[day] = Object.fromEntries(Object.entries(values).filter(([id]) => validQuest(id)).map(([id, xp]) => [id, integer(xp)]))
    })
  }
  const journal: PlayerState['journal'] = {}
  if (raw.journal && typeof raw.journal === 'object') {
    Object.entries(raw.journal).forEach(([day, entries]) => {
      if (!entries || typeof entries !== 'object') return
      journal[day] = Object.fromEntries(Object.entries(entries).map(([id, entry]) => [id, { note: String(entry?.note ?? '').slice(0, 5000) }]))
    })
  }
  const attributes = emptyAttributes()
  Object.keys(ATTRIBUTES).forEach((key) => { attributes[key as Attribute] = integer(raw.attributes?.[key as Attribute]) })
  const difficulty: Difficulty = raw.difficulty === 'light' || raw.difficulty === 'challenge' ? raw.difficulty : 'standard'
  const state: PlayerState = {
    ...base, totalXp: integer(raw.totalXp), attributes, history, dailySets, rewards, customTasks, journal, difficulty,
    unlockedAchievements: Array.isArray(raw.unlockedAchievements) ? raw.unlockedAchievements.filter((key) => typeof key === 'string' && /^\w+:[1-4]$/.test(key)) : [],
    weeklyGoals: raw.weeklyGoals && typeof raw.weeklyGoals === 'object' ? Object.fromEntries(Object.entries(raw.weeklyGoals).map(([key, value]) => [key, String(value).slice(0, 500)])) : {},
    weeklyDone: Array.isArray(raw.weeklyDone) ? raw.weeklyDone.filter((key) => typeof key === 'string') : [],
    restDays: Array.isArray(raw.restDays) ? raw.restDays.filter((key) => typeof key === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(key)) : [],
    completedChains: Array.isArray(raw.completedChains) ? raw.completedChains.filter((id) => CHAINS.some((chain) => chain.id === id)) : [],
    reminderEnabled: Boolean(raw.reminderEnabled), reminderMinute: Math.min(1439, integer(raw.reminderMinute, 1200)),
    pinHash: typeof raw.pinHash === 'string' ? raw.pinHash : '', playerName: String(raw.playerName ?? 'Игрок').trim().slice(0, 40) || 'Игрок',
    createdAt: typeof raw.createdAt === 'string' ? raw.createdAt : todayKey(),
  }
  ensureDaily(state, todayKey())
  syncAchievements(state, todayKey())
  return state
}
export function loadState(): PlayerState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? normalizeState(JSON.parse(saved)) : createInitialState()
  } catch {
    return createInitialState()
  }
}
export function levelProgress(totalXp: number) {
  let remaining = Math.max(0, totalXp)
  let level = 1
  while (true) {
    const needed = 100 + (level - 1) * 25
    if (remaining < needed) {
      const rank = level >= 25 ? 'S' : level >= 17 ? 'A' : level >= 12 ? 'B' : level >= 8 ? 'C' : level >= 4 ? 'D' : 'E'
      return { level, currentXp: remaining, neededXp: needed, rank }
    }
    remaining -= needed
    level += 1
  }
}
function seededRandom(seed: string) {
  let hash = 2166136261
  for (let index = 0; index < seed.length; index += 1) hash = Math.imul(hash ^ seed.charCodeAt(index), 16777619)
  return () => {
    hash += 0x6D2B79F5
    let value = hash
    value = Math.imul(value ^ (value >>> 15), value | 1)
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61)
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296
  }
}
export function generateDaily(day: string, level: number, previousIds: string[] = []): Quest[] {
  const random = seededRandom(`sistema:${day}`)
  const shuffle = <T,>(items: T[]) => {
    const result = [...items]
    for (let index = result.length - 1; index > 0; index -= 1) {
      const target = Math.floor(random() * (index + 1))
      ;[result[index], result[target]] = [result[target], result[index]]
    }
    return result
  }
  const rotating = shuffle<Quest['category']>(['recovery', 'social', 'finance', 'environment', 'creativity'])
  const categories: Quest['category'][] = ['body', 'mind', 'discipline', ...rotating.slice(0, 3)]
  const selected = categories.map((category) => {
    const eligible = QUESTS.filter((quest) => quest.category === category && quest.minLevel <= level)
    const preferred = eligible.filter((quest) => !previousIds.includes(quest.id))
    return shuffle(preferred.length ? preferred : eligible)[0]
  })
  return shuffle(selected)
}
export function ensureDaily(state: PlayerState, day: string): Quest[] {
  const existing = state.dailySets[day]
  if (existing?.length === DAILY_QUEST_COUNT && existing.every((id) => id in QUEST_BY_ID)) return existing.map((id) => QUEST_BY_ID[id])
  const quests = generateDaily(day, levelProgress(state.totalXp).level, state.dailySets[shiftDay(day, -1)] ?? [])
  state.dailySets[day] = quests.map((quest) => quest.id)
  return quests
}
export function allQuests(state: PlayerState): Record<string, Quest> {
  return { ...QUEST_BY_ID, ...Object.fromEntries(state.customTasks.map((task) => [task.id, customAsQuest(task)])) }
}
export function customAsQuest(task: CustomTask): Quest {
  return { id: task.id, title: task.title, description: task.description, category: task.category, xp: task.xp, minLevel: 1, base: 0, step: 0, maxTarget: 0 }
}
export function targetFor(quest: Quest, level: number, difficulty: Difficulty): number {
  if (!quest.base) return 0
  const normal = Math.min(quest.maxTarget, quest.base + quest.step * (Math.max(1, level) - 1))
  if (difficulty === 'light') return Math.max(1, Math.floor(normal * 0.75))
  if (difficulty === 'challenge') return Math.max(normal, Math.floor(normal * 1.25))
  return normal
}
export function scaledDescription(quest: Quest, level: number, difficulty: Difficulty): string {
  return quest.description.replaceAll('{target}', String(targetFor(quest, level, difficulty)))
}
export function adjustedReward(state: PlayerState, quest: Quest): number {
  const normal = quest.xp + Math.min(20, (levelProgress(state.totalXp).level - 1) * 2)
  if (state.difficulty === 'light') return Math.max(5, Math.floor(normal * 0.8))
  if (state.difficulty === 'challenge') return Math.floor(normal * 1.25)
  return normal
}
export function isDayComplete(state: PlayerState, day: string): boolean {
  if (state.restDays.includes(day)) return true
  const ids = state.dailySets[day] ?? generateDaily(day, 1).map((quest) => quest.id)
  return ids.every((id) => state.history[day]?.includes(id))
}
export function completedToday(state: PlayerState, day: string): number {
  const daily = new Set(state.dailySets[day] ?? [])
  return (state.history[day] ?? []).filter((id) => daily.has(id)).length
}
export function categoryCompletedOn(state: PlayerState, category: string, day: string): number {
  const quests = allQuests(state)
  return (state.history[day] ?? []).filter((id) => quests[id]?.category === category).length
}
export function categoryCompleted(state: PlayerState, category: string): number {
  const quests = allQuests(state)
  return Object.values(state.history).flat().filter((id) => quests[id]?.category === category).length
}
export function streak(state: PlayerState, today = todayKey()): number {
  let cursor = today
  let count = 0
  while (isDayComplete(state, cursor)) { count += 1; cursor = shiftDay(cursor, -1) }
  return count
}
export function perfectDays(state: PlayerState, today = todayKey()): number {
  return Object.keys(state.history).filter((day) => day <= today && !state.restDays.includes(day) && isDayComplete(state, day)).length
}
export function metricValue(state: PlayerState, metric: string, today = todayKey()): number {
  if (metric === 'completed') return Object.values(state.history).reduce((sum, ids) => sum + ids.length, 0)
  if (metric === 'streak') return streak(state, today)
  if (metric === 'level') return levelProgress(state.totalXp).level
  if (metric === 'perfect') return perfectDays(state, today)
  if (metric === 'xp') return state.totalXp
  if (metric === 'journal') return Object.values(state.journal).reduce((sum, entries) => sum + Object.keys(entries).length, 0)
  if (metric === 'boss') return state.weeklyDone.length
  if (metric === 'custom') {
    const ids = new Set(state.customTasks.map((task) => task.id))
    return Object.values(state.history).flat().filter((id) => ids.has(id)).length
  }
  if (metric === 'variety') {
    const quests = allQuests(state)
    return new Set(Object.values(state.history).flat().map((id) => quests[id]?.category).filter(Boolean)).size
  }
  if (metric === 'chains') return state.completedChains.length
  return categoryCompleted(state, metric)
}
export function syncAchievements(state: PlayerState, today = todayKey()): Achievement[] {
  const unlocked: Achievement[] = []
  ACHIEVEMENTS.forEach((achievement) => {
    const value = metricValue(state, achievement.metric, today)
    achievement.thresholds.forEach((threshold, index) => {
      const key = `${achievement.id}:${index + 1}`
      if (value >= threshold && !state.unlockedAchievements.includes(key)) {
        state.unlockedAchievements.push(key)
        unlocked.push(achievement)
      }
    })
  })
  return unlocked
}
export function chainProgress(state: PlayerState, chainId: string, today = todayKey()): number {
  const chain = CHAINS.find((item) => item.id === chainId)
  if (!chain) return 0
  let cursor = today
  let count = 0
  while (count < chain.days && categoryCompletedOn(state, chain.category, cursor) > 0) {
    count += 1
    cursor = shiftDay(cursor, -1)
  }
  return count
}
function applyChains(state: PlayerState, today: string): number {
  let bonus = 0
  CHAINS.forEach((chain) => {
    if (!state.completedChains.includes(chain.id) && chainProgress(state, chain.id, today) >= chain.days) {
      state.completedChains.push(chain.id)
      state.totalXp += chain.reward
      bonus += chain.reward
    }
  })
  return bonus
}
export interface ToggleResult { completing: boolean; reward: number; levelUp: boolean; unlocks: Achievement[]; chainBonus: number }
export function toggleQuest(state: PlayerState, quest: Quest, day = todayKey()): ToggleResult {
  ensureDaily(state, day)
  const oldLevel = levelProgress(state.totalXp).level
  const history = new Set(state.history[day] ?? [])
  const wasComplete = isDayComplete(state, day)
  const completing = !history.has(quest.id)
  const reward = adjustedReward(state, quest)
  if (completing) {
    history.add(quest.id)
    state.totalXp += reward
    state.attributes[CATEGORIES[quest.category].attribute] += 1
    state.rewards[day] = { ...(state.rewards[day] ?? {}), [quest.id]: reward }
  } else {
    if (wasComplete && !state.restDays.includes(day)) state.totalXp = Math.max(0, state.totalXp - DAILY_BONUS_XP)
    history.delete(quest.id)
    const awarded = state.rewards[day]?.[quest.id] ?? reward
    state.totalXp = Math.max(0, state.totalXp - awarded)
    state.attributes[CATEGORIES[quest.category].attribute] = Math.max(0, state.attributes[CATEGORIES[quest.category].attribute] - 1)
    delete state.rewards[day]?.[quest.id]
  }
  state.history[day] = [...history]
  if (completing && !wasComplete && isDayComplete(state, day)) state.totalXp += DAILY_BONUS_XP
  const chainBonus = applyChains(state, day)
  const unlocks = syncAchievements(state, day)
  return { completing, reward, levelUp: levelProgress(state.totalXp).level > oldLevel, unlocks, chainBonus }
}
export function toggleWeekly(state: PlayerState, day = todayKey()): boolean {
  const key = weekKey(day)
  if (!state.weeklyGoals[key]?.trim()) return false
  if (state.weeklyDone.includes(key)) {
    state.weeklyDone = state.weeklyDone.filter((item) => item !== key)
    state.totalXp = Math.max(0, state.totalXp - 100)
    syncAchievements(state, day)
    return false
  }
  state.weeklyDone.push(key)
  state.totalXp += 100
  syncAchievements(state, day)
  return true
}
export function toggleRest(state: PlayerState, day = todayKey()): boolean {
  if (state.restDays.includes(day)) state.restDays = state.restDays.filter((item) => item !== day)
  else state.restDays.push(day)
  syncAchievements(state, day)
  return state.restDays.includes(day)
}
export function weeklyRecommendation(state: PlayerState, today = todayKey()): string {
  const counts = Object.keys(CATEGORIES).map((category) => ({
    category: category as Quest['category'],
    count: Array.from({ length: 7 }, (_, offset) => categoryCompletedOn(state, category, shiftDay(today, -offset))).reduce((a, b) => a + b, 0),
  }))
  counts.sort((a, b) => a.count - b.count)
  return `Добавь внимание направлению «${CATEGORIES[counts[0].category].label}»: за последние 7 дней здесь меньше всего действий.`
}
