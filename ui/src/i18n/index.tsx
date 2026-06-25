import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { en, type Locale, type Messages } from './en'
import { ru } from './ru'

const STORAGE_KEY = 'peeknook_locale'

const catalogs: Record<Locale, Messages> = { en, ru }

type I18nContextValue = {
  locale: Locale
  setLocale: (l: Locale) => void
  t: Messages
}

const I18nContext = createContext<I18nContextValue | null>(null)

function readLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'ru' || saved === 'en') return saved
  return navigator.language.startsWith('ru') ? 'ru' : 'en'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readLocale)

  const setLocale = useCallback((l: Locale) => {
    localStorage.setItem(STORAGE_KEY, l)
    setLocaleState(l)
  }, [])

  const value = useMemo(
    () => ({ locale, setLocale, t: catalogs[locale] }),
    [locale, setLocale],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n outside provider')
  return ctx
}
