import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { useI18n } from './i18n'
import Home from './pages/Home'
import Notebooks from './pages/Notebooks'
import NotebookDetail from './pages/NotebookDetail'
import Settings from './pages/Settings'
import CloudSync from './pages/CloudSync'
import Search from './pages/Search'
import Transformations from './pages/Transformations'
import Podcasts from './pages/Podcasts'
import Team from './pages/Team'
import Billing from './pages/Billing'
import './App.css'

function Shell() {
  const { t, locale, setLocale } = useI18n()

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <header className="border-b border-stone-200 bg-white/90 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Peek<span className="text-amber-600">Nook</span>
          </Link>
          <nav className="flex flex-wrap items-center gap-3 text-sm">
            <Link to="/notebooks" className="hover:text-amber-700">{t.nav.notebooks}</Link>
            <Link to="/search" className="hover:text-amber-700">{t.nav.search}</Link>
            <Link to="/transformations" className="hover:text-amber-700">{t.nav.transform}</Link>
            <Link to="/podcasts" className="hover:text-amber-700">{t.nav.podcasts}</Link>
            <Link to="/cloud" className="hover:text-amber-700">{t.nav.cloud}</Link>
            <Link to="/team" className="hover:text-amber-700">{t.nav.team}</Link>
            <Link to="/billing" className="hover:text-amber-700">{t.nav.billing}</Link>
            <Link to="/settings" className="hover:text-amber-700">{t.nav.settings}</Link>
            <select
              aria-label={t.lang}
              className="rounded border border-stone-300 px-2 py-1 text-xs"
              value={locale}
              onChange={(e) => setLocale(e.target.value as 'en' | 'ru')}
            >
              <option value="en">EN</option>
              <option value="ru">RU</option>
            </select>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/notebooks" element={<Notebooks />} />
          <Route path="/notebooks/:id" element={<NotebookDetail />} />
          <Route path="/search" element={<Search />} />
          <Route path="/transformations" element={<Transformations />} />
          <Route path="/podcasts" element={<Podcasts />} />
          <Route path="/cloud" element={<CloudSync />} />
          <Route path="/team" element={<Team />} />
          <Route path="/billing" element={<Billing />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  )
}
