import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, FormEvent, ReactNode } from 'react'
import {
  Activity, Award, BarChart3, Bell, BookOpen, Brain, CalendarDays, Check, CheckCircle2,
  ChevronRight, Circle, Clock3, Crown, Download, Dumbbell, Flame, Heart, Home, Info,
  LayoutDashboard, Library, ListChecks, Lock, Menu, Moon, Palette, Plus,
  RotateCcw, Save, Search, Settings, Shield, Smartphone, Sparkles, Target,
  Trash2, Trophy, Upload, Users, Wallet, X, Zap,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import {
  ACHIEVEMENTS, ATTRIBUTES, CATEGORIES, CHAINS, DAILY_BONUS_XP, QUESTS, TIER_COLORS,
  TIER_NAMES,
} from './game/data'
import type { Attribute, Category, CustomTask, Difficulty, PlayerState, Quest } from './game/data'
import {
  STORAGE_KEY, adjustedReward, allQuests, categoryCompleted, chainProgress, completedToday,
  createInitialState, customAsQuest, ensureDaily, levelProgress, loadState, metricValue,
  normalizeState, scaledDescription, shiftDay, streak, syncAchievements, toggleQuest, toggleRest,
  toggleWeekly, todayKey, weekKey, weeklyRecommendation,
} from './game/engine'
import './App.css'

type Page = 'today' | 'goals' | 'catalog' | 'rewards' | 'more'
type MoreTab = 'journal' | 'analytics' | 'settings'
type ModalName = 'custom' | 'weekly' | 'install' | 'pin' | 'reset' | null

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const NAV: { id: Page; label: string; icon: LucideIcon }[] = [
  { id: 'today', label: 'Сегодня', icon: LayoutDashboard },
  { id: 'goals', label: 'Цели', icon: Target },
  { id: 'catalog', label: 'Каталог', icon: Library },
  { id: 'rewards', label: 'Награды', icon: Trophy },
  { id: 'more', label: 'Ещё', icon: Menu },
]
const DIFFICULTIES: { id: Difficulty; name: string; description: string }[] = [
  { id: 'light', name: 'Мягкий', description: '75% нормы · 80% опыта' },
  { id: 'standard', name: 'Стандарт', description: 'Полная норма · полный опыт' },
  { id: 'challenge', name: 'Вызов', description: '125% нормы · 125% опыта' },
]
const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function Rune({ small = false }: { small?: boolean }) {
  return <div className={`rune ${small ? 'rune-small' : ''}`} aria-hidden="true"><span /><i /></div>
}
function ProgressBar({ value, color = 'cyan' }: { value: number; color?: string }) {
  return <div className={`progress-track ${color}`}><span style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></div>
}
function CategoryIcon({ category, size = 17 }: { category: Category; size?: number }) {
  const icons: Record<Category, LucideIcon> = {
    body: Dumbbell, mind: Brain, discipline: Shield, recovery: Heart,
    social: Users, finance: Wallet, environment: Home, creativity: Palette,
  }
  const Icon = icons[category]
  return <Icon size={size} />
}
function Modal({ title, subtitle, onClose, children, wide = false }: {
  title: string; subtitle?: string; onClose: () => void; children: ReactNode; wide?: boolean
}) {
  const panel = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const oldOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    panel.current?.querySelector<HTMLElement>('input, textarea, button')?.focus()
    const listener = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', listener)
    return () => {
      document.body.style.overflow = oldOverflow
      window.removeEventListener('keydown', listener)
      previous?.focus()
    }
  }, [onClose])
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <div className={`modal ${wide ? 'modal-wide' : ''}`} role="dialog" aria-modal="true" aria-labelledby="modal-title" ref={panel}>
      <button className="icon-button modal-close" onClick={onClose} aria-label="Закрыть"><X size={20} /></button>
      <p className="eyebrow">СИСТЕМА / ПРОТОКОЛ</p>
      <h2 id="modal-title">{title}</h2>
      {subtitle && <p className="muted modal-subtitle">{subtitle}</p>}
      {children}
    </div>
  </div>
}
function SectionTitle({ eyebrow, title, action }: { eyebrow: string; title: string; action?: ReactNode }) {
  return <div className="section-title"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>{action}</div>
}
function QuestCard({ quest, state, day, onToggle, onJournal, custom = false }: {
  quest: Quest; state: PlayerState; day: string; onToggle: (quest: Quest) => void;
  onJournal?: (quest: Quest) => void; custom?: boolean
}) {
  const completed = state.history[day]?.includes(quest.id) ?? false
  const locked = levelProgress(state.totalXp).level < quest.minLevel
  const reward = adjustedReward(state, quest)
  const note = state.journal[day]?.[quest.id]?.note
  return <article className={`quest-card ${completed ? 'is-complete' : ''} ${locked ? 'is-locked' : ''}`}>
    <button className="quest-check" disabled={locked} onClick={() => onToggle(quest)} aria-label={completed ? `Отменить: ${quest.title}` : `Выполнить: ${quest.title}`}>
      {completed ? <Check size={19} strokeWidth={3} /> : locked ? <Lock size={15} /> : <Circle size={19} />}
    </button>
    <div className="quest-content">
      <div className="quest-meta"><span style={{ color: CATEGORIES[quest.category].color }}><CategoryIcon category={quest.category} size={14} />{CATEGORIES[quest.category].short}</span>{custom && <span className="custom-label">ЛИЧНОЕ</span>}</div>
      <h3>{quest.title}</h3>
      <p>{scaledDescription(quest, levelProgress(state.totalXp).level, state.difficulty)}</p>
      <div className="quest-bottom"><span className="xp-tag">+{reward} XP</span>{note && <span className="noted"><BookOpen size={13} /> Запись добавлена</span>}{locked && <span className="locked-label">Откроется на {quest.minLevel} уровне</span>}</div>
    </div>
    {completed && onJournal && <button className="icon-button journal-button" onClick={() => onJournal(quest)} aria-label={`Записать результат: ${quest.title}`}><BookOpen size={17} /></button>}
  </article>
}
function CustomTaskForm({ initial, onSave, onClose }: { initial?: CustomTask; onSave: (task: CustomTask) => void; onClose: () => void }) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [category, setCategory] = useState<Category>(initial?.category ?? 'discipline')
  const [xp, setXp] = useState(initial?.xp ?? 20)
  const [weekdays, setWeekdays] = useState<number[]>(initial?.weekdays ?? [1, 2, 3, 4, 5, 6, 7])
  const [error, setError] = useState('')
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (title.trim().length < 3) return setError('Название должно содержать минимум 3 символа.')
    if (description.trim().length < 10) return setError('Опиши наблюдаемый результат минимум в 10 символах.')
    if (!weekdays.length) return setError('Выбери хотя бы один день недели.')
    onSave({ id: initial?.id ?? `custom:${crypto.randomUUID()}`, title: title.trim(), description: description.trim(), category, xp, weekdays })
  }
  return <form className="form-stack" onSubmit={submit}>
    <label>Название<input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={100} placeholder="Например, тренировка спины" /></label>
    <label>Критерий выполнения<textarea value={description} onChange={(e) => setDescription(e.target.value)} maxLength={1000} rows={4} placeholder="Что именно должно быть сделано и как ты проверишь результат?" /></label>
    <div className="form-row"><label>Направление<select value={category} onChange={(e) => setCategory(e.target.value as Category)}>{Object.entries(CATEGORIES).map(([id, item]) => <option value={id} key={id}>{item.label}</option>)}</select></label><label>Награда, XP<input type="number" min={5} max={100} value={xp} onChange={(e) => setXp(Number(e.target.value))} /></label></div>
    <fieldset><legend>Дни выполнения</legend><div className="weekday-picker">{WEEKDAYS.map((day, index) => <button type="button" className={weekdays.includes(index + 1) ? 'selected' : ''} key={day} onClick={() => setWeekdays((days) => days.includes(index + 1) ? days.filter((item) => item !== index + 1) : [...days, index + 1])}>{day}</button>)}</div></fieldset>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="modal-actions"><button type="button" className="button secondary" onClick={onClose}>Отмена</button><button className="button primary" type="submit"><Save size={17} />{initial ? 'Сохранить' : 'Добавить задачу'}</button></div>
  </form>
}

export default function App() {
  const [state, setState] = useState<PlayerState>(loadState)
  const [page, setPage] = useState<Page>('today')
  const [moreTab, setMoreTab] = useState<MoreTab>('journal')
  const [day, setDay] = useState(todayKey)
  const [modal, setModal] = useState<ModalName>(null)
  const [editingTask, setEditingTask] = useState<CustomTask | undefined>()
  const [journalQuest, setJournalQuest] = useState<Quest | null>(null)
  const [journalText, setJournalText] = useState('')
  const [toast, setToast] = useState('')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<Category | 'all'>('all')
  const [visibleQuests, setVisibleQuests] = useState(24)
  const [weeklyText, setWeeklyText] = useState('')
  const [playerName, setPlayerName] = useState(state.playerName)
  const [pin, setPin] = useState('')
  const [pinRepeat, setPinRepeat] = useState('')
  const [pinError, setPinError] = useState('')
  const [locked, setLocked] = useState(Boolean(state.pinHash))
  const [unlockPin, setUnlockPin] = useState('')
  const [deferredInstall, setDeferredInstall] = useState<BeforeInstallPromptEvent | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const reminderDay = useRef('')
  const level = levelProgress(state.totalXp)
  const daily = ensureDaily(state, day)
  const done = completedToday(state, day)
  const dayComplete = done === daily.length
  const isRest = state.restDays.includes(day)
  const currentWeek = weekKey(day)
  const weeklyGoal = state.weeklyGoals[currentWeek] ?? ''
  const weeklyDone = state.weeklyDone.includes(currentWeek)
  const all = allQuests(state)
  const completedCount = metricValue(state, 'completed', day)
  const unlockedCount = state.unlockedAchievements.length

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)) } catch {
      window.setTimeout(() => setToast('Не удалось сохранить прогресс. Проверь свободное место.'), 0)
    }
  }, [state])
  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(''), 4200)
    return () => window.clearTimeout(timer)
  }, [toast])
  useEffect(() => {
    const checkDay = () => {
      const current = todayKey()
      if (current !== day) {
        setDay(current)
        setState((previous) => { const next = structuredClone(previous); ensureDaily(next, current); return next })
      }
    }
    const timer = window.setInterval(checkDay, 60000)
    document.addEventListener('visibilitychange', checkDay)
    window.addEventListener('focus', checkDay)
    return () => { window.clearInterval(timer); document.removeEventListener('visibilitychange', checkDay); window.removeEventListener('focus', checkDay) }
  }, [day])
  useEffect(() => {
    const listener = (event: Event) => { event.preventDefault(); setDeferredInstall(event as BeforeInstallPromptEvent) }
    window.addEventListener('beforeinstallprompt', listener)
    return () => window.removeEventListener('beforeinstallprompt', listener)
  }, [])
  useEffect(() => {
    const timer = window.setInterval(() => {
      const now = new Date()
      if (!state.reminderEnabled || state.reminderMinute !== now.getHours() * 60 + now.getMinutes() || reminderDay.current === todayKey()) return
      reminderDay.current = todayKey()
      const message = 'Система ждёт результатов. Проверь задания на сегодня.'
      setToast(message)
      if ('Notification' in window && Notification.permission === 'granted') new Notification('СИСТЕМА', { body: message, icon: 'icon-192.png' })
    }, 15000)
    return () => window.clearInterval(timer)
  }, [state.reminderEnabled, state.reminderMinute])

  const navigate = (target: Page) => { setPage(target); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  const handleToggle = (quest: Quest) => {
    const next = structuredClone(state)
    const result = toggleQuest(next, quest, day)
    setState(next)
    if (result.levelUp) setToast(`Новый уровень: ${levelProgress(next.totalXp).level}. Твоя мощь растёт.`)
    else if (!dayComplete && completedToday(next, day) === daily.length && result.completing) setToast(`День закрыт. Бонус за дисциплину: +${DAILY_BONUS_XP} XP`)
    else if (result.unlocks.length) setToast(`Достижение открыто: ${result.unlocks[0].title}`)
    else if (result.chainBonus) setToast(`Цепочка завершена: +${result.chainBonus} XP`)
    else setToast(result.completing ? `Принято. +${result.reward} XP` : 'Выполнение отменено, награда возвращена.')
  }
  const openJournal = (quest: Quest) => { setJournalQuest(quest); setJournalText(state.journal[day]?.[quest.id]?.note ?? '') }
  const saveJournal = (event: FormEvent) => {
    event.preventDefault()
    if (!journalQuest) return
    const next = structuredClone(state)
    next.journal[day] = { ...(next.journal[day] ?? {}) }
    if (journalText.trim()) next.journal[day][journalQuest.id] = { note: journalText.trim() }
    else delete next.journal[day][journalQuest.id]
    const before = next.unlockedAchievements.length
    syncAchievements(next, day)
    setState(next)
    setJournalQuest(null)
    setToast(next.unlockedAchievements.length > before ? 'Достижение «Летописец» обновлено.' : 'Запись сохранена в летописи.')
  }
  const saveCustom = (task: CustomTask) => {
    const next = structuredClone(state)
    const index = next.customTasks.findIndex((item) => item.id === task.id)
    if (index >= 0) next.customTasks[index] = task
    else next.customTasks.push(task)
    setState(next); setModal(null); setEditingTask(undefined)
    setToast(index >= 0 ? 'Личная задача обновлена.' : 'Новый личный протокол добавлен.')
  }
  const deleteCustom = (task: CustomTask) => {
    if (Object.values(state.history).some((ids) => ids.includes(task.id))) return setToast('Задачу с сохранёнными результатами нельзя удалить. Убери все дни в редакторе.')
    setState({ ...state, customTasks: state.customTasks.filter((item) => item.id !== task.id) })
    setToast('Личная задача удалена.')
  }
  const saveWeekly = (event: FormEvent) => {
    event.preventDefault()
    if (!weeklyText.trim()) return
    setState({ ...state, weeklyGoals: { ...state.weeklyGoals, [currentWeek]: weeklyText.trim() } })
    setModal(null); setToast('Недельная цель установлена.')
  }
  const exportData = () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a'); link.href = url; link.download = `sistema-backup-${day}.json`; link.click()
    URL.revokeObjectURL(url); setToast('Резервная копия выгружена.')
  }
  const importData = async (file?: File) => {
    if (!file) return
    try {
      const next = normalizeState(JSON.parse(await file.text()))
      setState(next); setPlayerName(next.playerName); setLocked(false); setToast('Прогресс восстановлен из копии.')
    } catch { setToast('Не удалось прочитать копию. Выбери JSON-файл Системы.') }
    if (fileInput.current) fileInput.current.value = ''
  }
  const digestPin = async (value: string) => {
    const bytes = new TextEncoder().encode(`sistema:${value}`)
    const hash = await crypto.subtle.digest('SHA-256', bytes)
    return Array.from(new Uint8Array(hash)).map((byte) => byte.toString(16).padStart(2, '0')).join('')
  }
  const savePin = async (event: FormEvent) => {
    event.preventDefault()
    if (!/^\d{4}$/.test(pin)) return setPinError('PIN должен состоять ровно из 4 цифр.')
    if (pin !== pinRepeat) return setPinError('Значения не совпадают.')
    const pinHash = await digestPin(pin)
    setState({ ...state, pinHash }); setModal(null); setPin(''); setPinRepeat(''); setPinError(''); setToast('Локальная защита включена.')
  }
  const unlock = async (event: FormEvent) => {
    event.preventDefault()
    if (await digestPin(unlockPin) === state.pinHash) { setLocked(false); setUnlockPin(''); setPinError('') }
    else { setPinError('Неверный PIN. Попробуй ещё раз.'); setUnlockPin('') }
  }
  const install = async () => {
    if (deferredInstall) {
      await deferredInstall.prompt()
      const choice = await deferredInstall.userChoice
      if (choice.outcome === 'accepted') setDeferredInstall(null)
    } else setModal('install')
  }
  const enableReminder = async (enabled: boolean) => {
    if (enabled && 'Notification' in window && Notification.permission === 'default') await Notification.requestPermission()
    setState({ ...state, reminderEnabled: enabled })
    setToast(enabled ? 'Напоминание включено — работает, пока приложение открыто.' : 'Напоминание выключено.')
  }

  const filteredQuests = useMemo(() => QUESTS.filter((quest) => {
    const query = search.trim().toLocaleLowerCase('ru')
    return (category === 'all' || quest.category === category) && (!query || `${quest.title} ${quest.description}`.toLocaleLowerCase('ru').includes(query))
  }), [search, category])
  const historyEntries = Object.entries(state.history).flatMap(([entryDay, ids]) => ids.map((id) => ({ day: entryDay, quest: all[id] })).filter((item) => item.quest)).sort((a, b) => b.day.localeCompare(a.day))
  const lastSeven = Array.from({ length: 7 }, (_, index) => {
    const key = shiftDay(day, index - 6)
    return { key, label: new Intl.DateTimeFormat('ru-RU', { weekday: 'short' }).format(new Date(`${key}T12:00:00`)).replace('.', ''), value: state.history[key]?.length ?? 0 }
  })
  const maxDaily = Math.max(6, ...lastSeven.map((item) => item.value))

  if (locked) return <main className="lock-screen"><Rune /><p className="eyebrow">ДОСТУП ОГРАНИЧЕН</p><h1>СИСТЕМА</h1><p className="muted">Введи PIN, чтобы продолжить путь.</p><form onSubmit={unlock}><input className="pin-input" type="password" inputMode="numeric" pattern="[0-9]*" maxLength={4} value={unlockPin} onChange={(e) => setUnlockPin(e.target.value.replace(/\D/g, ''))} placeholder="••••" aria-label="PIN-код" autoFocus />{pinError && <p className="form-error">{pinError}</p>}<button className="button primary" type="submit"><Lock size={17} />Разблокировать</button></form><small>Данные хранятся только на этом устройстве.</small></main>

  return <div className="app-shell">
    <aside className="sidebar">
      <button className="brand" onClick={() => navigate('today')} aria-label="Система — на главную"><Rune small /><span>СИСТЕМА<small>ИНТЕРФЕЙС ОХОТНИКА</small></span></button>
      <nav>{NAV.map(({ id, label, icon: Icon }) => <button className={page === id ? 'active' : ''} key={id} onClick={() => navigate(id)}><Icon size={19} /><span>{label}</span>{page === id && <ChevronRight size={15} />}</button>)}</nav>
      <div className="sidebar-bottom"><div className="mini-rank"><span>{level.rank}</span><div><small>ТЕКУЩИЙ РАНГ</small><strong>Уровень {level.level}</strong></div></div><p>Прокачивай не персонажа.<br />Прокачивай себя.</p></div>
    </aside>

    <div className="main-column">
      <header className="topbar"><div className="mobile-brand"><Rune small /><strong>СИСТЕМА</strong></div><div className="topbar-player"><span className="status-dot" /><span>{state.playerName}</span><b>РАНГ {level.rank}</b></div><button className="icon-button" onClick={() => { setMoreTab('settings'); navigate('more') }} aria-label="Настройки"><Settings size={19} /></button></header>
      <main className="content">
        {page === 'today' && <div className="page-enter">
          <section className="hero-panel">
            <div className="hero-sigil" aria-hidden="true"><i /><i /><i /><b>✦</b></div>
            <div className="hero-copy"><p className="eyebrow"><span className="live-dot" /> ЕЖЕДНЕВНЫЙ ПРОТОКОЛ</p><p className="hero-date">{new Intl.DateTimeFormat('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())}</p><h1>{dayComplete ? 'День покорён.' : isRest ? 'Восстановление — тоже прогресс.' : 'Стань сильнее, чем вчера.'}</h1><p className="hero-subtitle">{dayComplete ? 'Все обязательные задания закрыты. Система признаёт твою дисциплину.' : isRest ? 'День отдыха сохраняет серию без бонуса за полный день.' : 'Реальные действия. Измеримый результат. Никаких пустых обещаний.'}</p><div className="hero-stats"><div><Flame size={18} /><strong>{streak(state, day)}</strong><span>дней в серии</span></div><div><Zap size={18} /><strong>{state.totalXp}</strong><span>всего XP</span></div></div></div>
            <div className="level-orb" style={{ '--progress': `${(level.currentXp / level.neededXp) * 360}deg` } as CSSProperties}><div><small>УРОВЕНЬ</small><strong>{level.level}</strong><span>РАНГ {level.rank}</span></div></div>
            <div className="level-progress"><div><span>{level.currentXp} / {level.neededXp} XP</span><span>до {level.level + 1} уровня</span></div><ProgressBar value={(level.currentXp / level.neededXp) * 100} /></div>
          </section>

          <div className="dashboard-grid">
            <section><SectionTitle eyebrow={`${done} ИЗ ${daily.length} ВЫПОЛНЕНО`} title="Задания на сегодня" action={<button className={`rest-button ${isRest ? 'active' : ''}`} onClick={() => { const next = structuredClone(state); const enabled = toggleRest(next, day); setState(next); setToast(enabled ? 'День отдыха активирован.' : 'Обычный режим восстановлен.') }}><Moon size={15} />{isRest ? 'Отдых включён' : 'День отдыха'}</button>} />
              <div className="daily-summary"><ProgressBar value={(done / daily.length) * 100} /><span>{Math.round((done / daily.length) * 100)}%</span><small>Полный день: <b>+{DAILY_BONUS_XP} XP</b></small></div>
              <div className="quest-list">{daily.map((quest) => <QuestCard key={quest.id} quest={quest} state={state} day={day} onToggle={handleToggle} onJournal={openJournal} />)}</div>
            </section>
            <aside className="dashboard-side">
              <section className={`boss-card ${weeklyDone ? 'completed' : ''}`}><div className="boss-icon"><Crown size={23} /></div><p className="eyebrow">БОСС НЕДЕЛИ</p><h3>{weeklyGoal || 'Главная цель ещё не выбрана'}</h3><p>{weeklyGoal ? 'Одна конкретная победа, которая задаст темп всей неделе.' : 'Запиши измеримый результат, которого хочешь достичь до конца недели.'}</p><div className="boss-actions"><button className="button gold" onClick={() => { if (!weeklyGoal) { setWeeklyText(''); setModal('weekly') } else { const next = structuredClone(state); const result = toggleWeekly(next, day); setState(next); setToast(result ? 'Босс повержен: +100 XP' : 'Победа отменена, 100 XP возвращены.') } }}>{weeklyDone ? <CheckCircle2 size={17} /> : <Target size={17} />}{weeklyDone ? 'Победа засчитана' : weeklyGoal ? 'Завершить цель' : 'Выбрать цель'}</button>{weeklyGoal && <button className="icon-button" onClick={() => { setWeeklyText(weeklyGoal); setModal('weekly') }} aria-label="Изменить недельную цель"><Settings size={16} /></button>}</div></section>
              <section className="panel compact-panel"><SectionTitle eyebrow="ЛИЧНЫЙ МАРШРУТ" title="Твои задачи" action={<button className="icon-button" onClick={() => { setEditingTask(undefined); setModal('custom') }} aria-label="Добавить личную задачу"><Plus size={19} /></button>} />{state.customTasks.filter((task) => task.weekdays.includes(new Date().getDay() || 7)).slice(0, 3).map((task) => <div className="mini-task" key={task.id}><button className={`small-check ${state.history[day]?.includes(task.id) ? 'checked' : ''}`} onClick={() => handleToggle(customAsQuest(task))}>{state.history[day]?.includes(task.id) && <Check size={13} />}</button><span>{task.title}</span></div>)}{!state.customTasks.some((task) => task.weekdays.includes(new Date().getDay() || 7)) && <p className="empty-copy">Добавь привычку под свою реальную цель.</p>}<button className="text-button" onClick={() => navigate('goals')}>Все цели <ChevronRight size={15} /></button></section>
              <section className="quote-panel"><Sparkles size={18} /><p>«Ты не обязан быть идеальным. Но можешь сделать следующий шаг».</p></section>
            </aside>
          </div>
        </div>}

        {page === 'goals' && <div className="page-enter"><SectionTitle eyebrow="ТВОЙ МАРШРУТ" title="Цели и долгие протоколы" action={<button className="button primary" onClick={() => { setEditingTask(undefined); setModal('custom') }}><Plus size={18} />Новая задача</button>} />
          <div className="goals-layout"><section><div className="subsection-heading"><h3>Личные задачи</h3><span>{state.customTasks.length}</span></div>{state.customTasks.length ? <div className="quest-list">{state.customTasks.map((task) => <div className="custom-wrapper" key={task.id}><QuestCard quest={customAsQuest(task)} state={state} day={day} onToggle={handleToggle} onJournal={openJournal} custom /><div className="custom-actions"><button onClick={() => { setEditingTask(task); setModal('custom') }}><Settings size={14} />Изменить</button><button onClick={() => deleteCustom(task)}><Trash2 size={14} />Удалить</button><span>{task.weekdays.length === 7 ? 'Каждый день' : task.weekdays.map((item) => WEEKDAYS[item - 1]).join(', ')}</span></div></div>)}</div> : <div className="empty-state"><ListChecks size={32} /><h3>Создай собственный протокол</h3><p>Задай точное действие, награду и дни, в которые Система будет показывать его на главной.</p><button className="button secondary" onClick={() => setModal('custom')}><Plus size={17} />Добавить первую задачу</button></div>}</section>
            <aside><section className="boss-card"><p className="eyebrow">ЦЕЛЬ НА {currentWeek}</p><h3>{weeklyGoal || 'Победа недели не выбрана'}</h3><p>{weeklyRecommendation(state, day)}</p><button className="button gold" onClick={() => { setWeeklyText(weeklyGoal); setModal('weekly') }}><Target size={17} />{weeklyGoal ? 'Изменить цель' : 'Установить цель'}</button></section></aside></div>
          <section className="chains-section"><SectionTitle eyebrow="ПОСЛЕДОВАТЕЛЬНОСТЬ" title="Цепочки" /><div className="chains-grid">{CHAINS.map((chain) => { const progress = chainProgress(state, chain.id, day); const finished = state.completedChains.includes(chain.id); return <article className={`chain-card ${finished ? 'finished' : ''}`} key={chain.id}><div className="chain-top"><span style={{ color: CATEGORIES[chain.category].color }}><CategoryIcon category={chain.category} /></span>{finished ? <Award size={19} /> : <small>+{chain.reward} XP</small>}</div><h3>{chain.title}</h3><p>{finished ? 'Цепочка завершена' : `${progress} / ${chain.days} дней`}</p><ProgressBar value={(progress / chain.days) * 100} color={finished ? 'gold' : 'cyan'} /></article> })}</div></section>
        </div>}

        {page === 'catalog' && <div className="page-enter"><SectionTitle eyebrow="АРХИВ СИСТЕМЫ" title="248 протоколов развития" /><div className="catalog-tools"><label className="search-box"><Search size={18} /><input value={search} onChange={(e) => { setSearch(e.target.value); setVisibleQuests(24) }} placeholder="Найти задание или действие…" /><span>{filteredQuests.length}</span></label><div className="category-filters"><button className={category === 'all' ? 'active' : ''} onClick={() => { setCategory('all'); setVisibleQuests(24) }}>Все</button>{Object.entries(CATEGORIES).map(([id, item]) => <button className={category === id ? 'active' : ''} key={id} onClick={() => { setCategory(id as Category); setVisibleQuests(24) }}>{item.label}</button>)}</div></div>
          <div className="catalog-notice"><Info size={16} /><span>Любое открытое задание можно засчитать сегодня. Норма растёт вместе с уровнем.</span></div>
          {filteredQuests.length ? <div className="catalog-grid">{filteredQuests.slice(0, visibleQuests).map((quest) => <QuestCard key={quest.id} quest={quest} state={state} day={day} onToggle={handleToggle} onJournal={openJournal} />)}</div> : <div className="empty-state"><Search size={32} /><h3>Ничего не найдено</h3><p>Измени запрос или выбери другое направление.</p></div>}
          {visibleQuests < filteredQuests.length && <button className="button secondary load-more" onClick={() => setVisibleQuests((count) => count + 24)}>Показать ещё <span>{Math.min(24, filteredQuests.length - visibleQuests)}</span></button>}
        </div>}

        {page === 'rewards' && <div className="page-enter"><SectionTitle eyebrow="ЗАЛ СЛАВЫ" title="Достижения и характеристики" /><div className="reward-summary"><div><Trophy size={25} /><strong>{unlockedCount}</strong><span>из 72 ступеней</span></div><ProgressBar value={(unlockedCount / 72) * 100} color="gold" /><p>Каждое достижение имеет 4 уровня: от бронзы до платины.</p></div>
          <section className="attributes-panel"><div className="subsection-heading"><h3>Характеристики игрока</h3><span>Растут за реальные действия</span></div><div className="attributes-grid">{Object.entries(ATTRIBUTES).map(([id, label]) => <div className="attribute" key={id}><span>{label}</span><strong>{state.attributes[id as Attribute]}</strong><ProgressBar value={Math.min(100, state.attributes[id as Attribute] * 4)} /></div>)}</div></section>
          <div className="achievements-grid">{ACHIEVEMENTS.map((achievement, index) => {
            const tier = [1, 2, 3, 4].filter((levelIndex) => state.unlockedAchievements.includes(`${achievement.id}:${levelIndex}`)).length
            const value = metricValue(state, achievement.metric, day)
            const nextThreshold = achievement.thresholds[Math.min(tier, 3)]
            const hidden = achievement.secret && tier === 0
            return <article className={`achievement-card tier-${tier}`} key={achievement.id}><div className="achievement-medal" style={{ '--tier-color': tier ? TIER_COLORS[tier - 1] : '#40505e' } as CSSProperties}><span>{hidden ? '?' : String(index + 1).padStart(2, '0')}</span></div><div className="achievement-info"><div className="achievement-heading"><p className="eyebrow">{tier ? TIER_NAMES[tier - 1] : hidden ? 'СЕКРЕТНО' : 'НЕ ОТКРЫТО'}</p><span>{tier} / 4</span></div><h3>{hidden ? 'Неизвестная награда' : achievement.title}</h3><p>{hidden ? 'Продолжай исследовать возможности Системы.' : achievement.description}</p><div className="achievement-progress"><ProgressBar value={tier === 4 ? 100 : (value / nextThreshold) * 100} color={tier === 4 ? 'gold' : 'cyan'} /><span>{tier === 4 ? 'МАКСИМУМ' : `${Math.min(value, nextThreshold)} / ${nextThreshold}`}</span></div></div></article>
          })}</div>
        </div>}

        {page === 'more' && <div className="page-enter"><SectionTitle eyebrow="ЦЕНТР УПРАВЛЕНИЯ" title="Летопись, аналитика и настройки" /><div className="more-tabs"><button className={moreTab === 'journal' ? 'active' : ''} onClick={() => setMoreTab('journal')}><BookOpen size={17} />Дневник</button><button className={moreTab === 'analytics' ? 'active' : ''} onClick={() => setMoreTab('analytics')}><BarChart3 size={17} />Аналитика</button><button className={moreTab === 'settings' ? 'active' : ''} onClick={() => setMoreTab('settings')}><Settings size={17} />Настройки</button></div>
          {moreTab === 'journal' && <section><div className="journal-intro"><div><p className="eyebrow">ЛЕТОПИСЬ ОХОТНИКА</p><h3>Фиксируй не только действие, но и результат</h3><p>К записи можно вернуться из карточки любого выполненного задания.</p></div><BookOpen size={42} /></div>{historyEntries.length ? <div className="history-list">{historyEntries.slice(0, 60).map(({ day: entryDay, quest }) => <article key={`${entryDay}-${quest.id}`}><div className="history-date"><CalendarDays size={15} /><span>{new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', year: entryDay.slice(0, 4) !== day.slice(0, 4) ? 'numeric' : undefined }).format(new Date(`${entryDay}T12:00:00`))}</span><i style={{ background: CATEGORIES[quest.category].color }} /></div><div><h3>{quest.title}</h3><p>{state.journal[entryDay]?.[quest.id]?.note || 'Результат ещё не записан.'}</p></div>{entryDay === day ? <button className="button secondary small" onClick={() => openJournal(quest)}><BookOpen size={15} />{state.journal[entryDay]?.[quest.id]?.note ? 'Изменить' : 'Записать'}</button> : <span className="history-xp">+{state.rewards[entryDay]?.[quest.id] ?? quest.xp} XP</span>}</article>)}</div> : <div className="empty-state"><BookOpen size={32} /><h3>Летопись пока пуста</h3><p>Выполни первое задание и запиши, что изменилось на самом деле.</p><button className="button primary" onClick={() => navigate('today')}>К заданиям</button></div>}</section>}
          {moreTab === 'analytics' && <section className="analytics-layout"><div className="metric-grid"><div><Activity size={19} /><span>Выполнено всего</span><strong>{completedCount}</strong></div><div><Flame size={19} /><span>Текущая серия</span><strong>{streak(state, day)} <small>дн.</small></strong></div><div><CheckCircle2 size={19} /><span>Полных дней</span><strong>{metricValue(state, 'perfect', day)}</strong></div><div><Clock3 size={19} /><span>Дней в Системе</span><strong>{Math.max(1, Math.floor((new Date(`${day}T12:00:00`).getTime() - new Date(`${state.createdAt}T12:00:00`).getTime()) / 86400000) + 1)}</strong></div></div><section className="panel chart-panel"><div className="subsection-heading"><div><p className="eyebrow">ДИНАМИКА</p><h3>Действия за 7 дней</h3></div><span>{lastSeven.reduce((sum, item) => sum + item.value, 0)} выполнено</span></div><div className="bar-chart">{lastSeven.map((item) => <div key={item.key}><span className="bar-value">{item.value || ''}</span><div className="bar-track"><i style={{ height: `${Math.max(item.value ? 8 : 2, (item.value / maxDaily) * 100)}%` }} /></div><small>{item.label}</small></div>)}</div></section><section className="panel"><div className="subsection-heading"><h3>Баланс направлений</h3><span>Все время</span></div><div className="category-stats">{Object.entries(CATEGORIES).map(([id, item]) => <div key={id}><span><CategoryIcon category={id as Category} size={15} />{item.label}</span><ProgressBar value={Math.min(100, categoryCompleted(state, id) * 5)} /><strong>{categoryCompleted(state, id)}</strong></div>)}</div></section><div className="recommendation"><Sparkles size={21} /><div><strong>Рекомендация Системы</strong><p>{weeklyRecommendation(state, day)}</p></div></div></section>}
          {moreTab === 'settings' && <section className="settings-grid"><div>
            <section className="panel settings-section"><div className="settings-heading"><Shield size={20} /><div><h3>Режим сложности</h3><p>Норма и награда меняются вместе.</p></div></div><div className="difficulty-options">{DIFFICULTIES.map((item) => <button className={state.difficulty === item.id ? 'active' : ''} key={item.id} onClick={() => { setState({ ...state, difficulty: item.id }); setToast(`Режим «${item.name}» активирован.`) }}><span>{item.name}</span><small>{item.description}</small>{state.difficulty === item.id && <Check size={16} />}</button>)}</div></section>
            <section className="panel settings-section"><div className="settings-heading"><Bell size={20} /><div><h3>Ежедневное напоминание</h3><p>Работает, пока веб-приложение открыто.</p></div><button className={`switch ${state.reminderEnabled ? 'on' : ''}`} role="switch" aria-checked={state.reminderEnabled} onClick={() => enableReminder(!state.reminderEnabled)}><span /></button></div><label className="time-setting">Время<input type="time" disabled={!state.reminderEnabled} value={`${String(Math.floor(state.reminderMinute / 60)).padStart(2, '0')}:${String(state.reminderMinute % 60).padStart(2, '0')}`} onChange={(e) => { const [hours, minutes] = e.target.value.split(':').map(Number); setState({ ...state, reminderMinute: hours * 60 + minutes }) }} /></label></section>
            <section className="panel settings-section"><div className="settings-heading"><Lock size={20} /><div><h3>Локальная защита</h3><p>PIN скрывает прогресс при следующем открытии.</p></div></div><div className="inline-actions"><button className="button secondary" onClick={() => { setPin(''); setPinRepeat(''); setPinError(''); setModal('pin') }}>{state.pinHash ? 'Сменить PIN' : 'Установить PIN'}</button>{state.pinHash && <><button className="button secondary" onClick={() => { setLocked(true); setToast('Система заблокирована.') }}>Заблокировать</button><button className="text-button danger" onClick={() => { setState({ ...state, pinHash: '' }); setToast('PIN удалён.') }}>Удалить PIN</button></>}</div></section>
          </div><div>
            <section className="panel settings-section"><div className="settings-heading"><Settings size={20} /><div><h3>Профиль игрока</h3><p>Это имя видно только тебе.</p></div></div><form className="name-form" onSubmit={(event) => { event.preventDefault(); if (!playerName.trim()) return; setState({ ...state, playerName: playerName.trim() }); setToast('Имя игрока сохранено.') }}><input value={playerName} maxLength={40} onChange={(e) => setPlayerName(e.target.value)} aria-label="Имя игрока" /><button className="button secondary" type="submit"><Save size={16} />Сохранить</button></form></section>
            <section className="panel settings-section install-panel"><div className="settings-heading"><Smartphone size={20} /><div><h3>Система всегда рядом</h3><p>Установи на компьютер или iPhone. Работает офлайн.</p></div></div><button className="button primary" onClick={install}><Download size={17} />Установить приложение</button><small>Обновления загружаются автоматически при открытии.</small></section>
            <section className="panel settings-section"><div className="settings-heading"><Save size={20} /><div><h3>Резервные копии</h3><p>Переноси прогресс вручную между устройствами.</p></div></div><div className="inline-actions"><button className="button secondary" onClick={exportData}><Download size={16} />Экспорт JSON</button><button className="button secondary" onClick={() => fileInput.current?.click()}><Upload size={16} />Импорт</button><input type="file" accept="application/json,.json" hidden ref={fileInput} onChange={(e) => importData(e.target.files?.[0])} /></div></section>
            <section className="panel settings-section danger-zone"><div className="settings-heading"><RotateCcw size={20} /><div><h3>Новый путь</h3><p>Стереть уровень, историю, задачи и настройки.</p></div></div><button className="button danger-button" onClick={() => setModal('reset')}>Сбросить весь прогресс</button></section>
          </div></section>}
        </div>}
      </main>
      <footer className="footer"><span>СИСТЕМА · WEB 4.0</span><span><span className="status-dot" /> Данные сохранены локально</span></footer>
    </div>

    <nav className="mobile-nav">{NAV.map(({ id, label, icon: Icon }) => <button className={page === id ? 'active' : ''} key={id} onClick={() => navigate(id)}><Icon size={20} /><span>{label}</span></button>)}</nav>

    {modal === 'custom' && <Modal title={editingTask ? 'Изменить личную задачу' : 'Новый личный протокол'} subtitle="Задание должно заканчиваться понятным, проверяемым результатом." onClose={() => { setModal(null); setEditingTask(undefined) }}><CustomTaskForm initial={editingTask} onSave={saveCustom} onClose={() => { setModal(null); setEditingTask(undefined) }} /></Modal>}
    {modal === 'weekly' && <Modal title="Босс недели" subtitle="Не список дел, а один главный измеримый результат на эту неделю." onClose={() => setModal(null)}><form className="form-stack" onSubmit={saveWeekly}><label>Недельная цель<textarea rows={4} autoFocus value={weeklyText} maxLength={500} onChange={(e) => setWeeklyText(e.target.value)} placeholder="Например: завершить 3 тренировки по 30 минут и записать результаты" required /></label><p className="form-hint">Награда за победу — 100 XP. Отмена победы возвращает награду.</p><div className="modal-actions"><button type="button" className="button secondary" onClick={() => setModal(null)}>Отмена</button><button className="button gold" type="submit"><Crown size={17} />Установить цель</button></div></form></Modal>}
    {journalQuest && <Modal title="Запись в летопись" subtitle={journalQuest.title} onClose={() => setJournalQuest(null)}><form className="form-stack" onSubmit={saveJournal}><label>Что получилось на самом деле?<textarea rows={6} autoFocus maxLength={5000} value={journalText} onChange={(e) => setJournalText(e.target.value)} placeholder="Результат, самочувствие, цифра, вывод или следующий шаг…" /></label><p className="form-hint">Запись останется только на этом устройстве и попадёт в резервную копию.</p><div className="modal-actions"><button className="button secondary" type="button" onClick={() => setJournalQuest(null)}>Отмена</button><button className="button primary" type="submit"><BookOpen size={17} />Сохранить запись</button></div></form></Modal>}
    {modal === 'install' && <Modal title="Установить Систему" subtitle="Приложение будет открываться отдельно и работать без интернета после первой загрузки." onClose={() => setModal(null)}><div className="install-guide"><div><span>01</span><section><h3>На iPhone</h3><p>Открой сайт в Safari. Нажми «Поделиться» → «Добавить на экран “Домой”» → «Добавить».</p></section></div><div><span>02</span><section><h3>На компьютере</h3><p>В Chrome или Edge нажми значок установки справа в адресной строке. Если его нет — меню → «Установить приложение».</p></section></div><div><span>03</span><section><h3>Обновления</h3><p>Открывай установленную Систему при подключении к интернету. Новая версия применится автоматически.</p></section></div></div><button className="button primary full-width" onClick={() => setModal(null)}>Понятно</button></Modal>}
    {modal === 'pin' && <Modal title={state.pinHash ? 'Новый PIN' : 'Защита Системы'} subtitle="Четыре цифры для локальной блокировки экрана. Это не шифрование резервной копии." onClose={() => setModal(null)}><form className="form-stack" onSubmit={savePin}><div className="form-row"><label>PIN<input type="password" inputMode="numeric" maxLength={4} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))} placeholder="4 цифры" /></label><label>Повтор<input type="password" inputMode="numeric" maxLength={4} value={pinRepeat} onChange={(e) => setPinRepeat(e.target.value.replace(/\D/g, ''))} placeholder="Ещё раз" /></label></div>{pinError && <p className="form-error">{pinError}</p>}<button className="button primary full-width" type="submit"><Lock size={17} />Сохранить PIN</button></form></Modal>}
    {modal === 'reset' && <Modal title="Начать с нуля?" subtitle="Это действие удалит весь прогресс на этом устройстве. Отменить его можно только импортом заранее сохранённой копии." onClose={() => setModal(null)}><div className="reset-warning"><Info size={22} /><p>Сначала рекомендуем экспортировать JSON в настройках.</p></div><div className="modal-actions"><button className="button secondary" onClick={() => setModal(null)}>Оставить прогресс</button><button className="button danger-button" onClick={() => { const next = createInitialState(); setState(next); setPlayerName(next.playerName); setModal(null); navigate('today'); setToast('Новый путь начат.') }}><Trash2 size={17} />Стереть всё</button></div></Modal>}
    {toast && <div className="toast" role="status"><CheckCircle2 size={19} /><span>{toast}</span><button onClick={() => setToast('')} aria-label="Закрыть уведомление"><X size={16} /></button></div>}
  </div>
}
