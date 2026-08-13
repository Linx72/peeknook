export default function DesktopStartup({ error }: { error?: string }) {
  const isRussian = (localStorage.getItem('peeknook_locale') || navigator.language).startsWith('ru')
  const title = error
    ? isRussian ? 'PeekNook не удалось запустить' : 'PeekNook could not start'
    : isRussian ? 'PeekNook запускается…' : 'PeekNook is starting…'
  const message = error
    ? isRussian
      ? 'Локальный сервис не ответил. Закройте приложение, запустите его снова и проверьте журнал PeekNook.'
      : 'The local service did not respond. Close the app, start it again, and check the PeekNook log.'
    : isRussian
      ? 'Подготавливаем локальную базу и поиск. Первый запуск может занять немного больше времени.'
      : 'Preparing the local database and search. The first launch may take a little longer.'

  return (
    <main className="flex min-h-screen items-center justify-center bg-stone-50 p-6 text-stone-900">
      <section className="w-full max-w-lg rounded-2xl border border-stone-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <p className="mt-3 text-sm text-stone-600">{message}</p>
        {error && <code className="mt-4 block break-words rounded bg-stone-100 p-3 text-xs">{error}</code>}
      </section>
    </main>
  )
}
