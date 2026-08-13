# PeekNook: RepoBase как источник истины

## Принятое решение

Каноническое место исходного кода PeekNook — ваш RepoBase/Forgejo:

```text
https://repobase.ru/timeweb/peeknook
git@repobase.ru:timeweb/peeknook.git
```

13 августа 2026 года приватный репозиторий `timeweb/peeknook` создан в RepoBase, а санитизированная ветка `main` опубликована и назначена локальной upstream-веткой. Перед первым push история была проверена и переписана только для удаления `cloud/peeknook_cloud_dev.sqlite`: ни текущая база, ни её старые версии в RepoBase не попали. Сам локальный файл сохранён на диске и покрыт `.gitignore`.

Репозиторий создавался через официальный Forgejo API по административному SSH-каналу. Использованные одноразовые PAT удалены сразу после операции; постоянные пользовательские токены и пароль аккаунта не менялись.

## Что уже подготовлено

- `.forgejo/workflows/ci.yml` — безопасный Linux source-CI: Python syntax/release policy, Bash syntax, UI build, TermitPro compile и conflict-marker gate. Пока общий runner не изолирован, workflow намеренно запускается только после push в `main` или вручную, а не на коде неизвестных fork pull request.
- `scripts/peeknook-repobase-preflight.sh` — read-only проверка точного RepoBase URL, существования репозитория, remote, ветки и чистоты checkout.
- `scripts/peeknook-legacy-github-guard.sh` — блокирует GitHub push/release по умолчанию.
- `scripts/peeknook-push-release.sh` теперь ожидает remote `repobase` и больше не откатывается незаметно на `origin`.

GitHub-мутирующие операции разрешаются только явным временным флагом:

```bash
export PEEKNOOK_ALLOW_GITHUB_LEGACY_RELEASE=1
```

Этот флаг означает только осознанный мост и не меняет источник истины обратно на GitHub.

## Защита `main`

В RepoBase действует branch-protection rule `main`:

- обычный push разрешён только команде `admins`;
- merge разрешён только команде `admins`;
- правило применяется и к администраторам, поэтому административный статус сам по себе его не обходит;
- force-push заблокирован защитой ветки;
- отклонённый review и устаревшая относительно base ветка блокируют merge;
- старые approvals сбрасываются после изменения кода.

Отдельное tag-protection rule `v*` разрешает создавать или изменять release-теги только команде `admins`. Массовая публикация тегов и force-перезапись release-ссылок не используются.

Пока намеренно не включены required status checks, обязательные подписи commit и минимальное число approvals. Текущий Forgejo workflow запускается после push в `main`, а общий Linux runner используется только для доверенного кода. Если потребовать этот post-push status до merge, получится невыполнимый цикл. Следующее усиление возможно после появления безопасного same-repository PR workflow и второго reviewer либо отдельного изолированного runner.

## Почему release CI пока нельзя просто перенести

Текущие Forgejo runners имеют Linux/Docker labels. Они подходят для проверки исходного кода, но не могут честно собрать и проверить:

- подписанный и notarized macOS DMG;
- приложение внутри macOS updater-архива;
- Windows MSI/NSIS с Authenticode.

Для полного отказа от GitHub native CI нужны отдельные доверенные runners:

1. macOS runner с Xcode tools, Developer ID certificate и Apple notarization credentials;
2. Windows runner с Windows SDK/signing tools и code-signing certificate;
3. изоляция runner от основного Forgejo host;
4. те же fail-closed проверки, которые уже добавлены в PeekNook release workflow.

Текущая инфраструктура RepoBase сама указывает, что Linux DinD runner остаётся trusted-code boundary. Поэтому macOS/Windows сертификаты нельзя переносить туда «для удобства».

## Исходный код и файлы обновления — разные вещи

RepoBase может быть приватным источником кода. Но обычное установленное приложение не сможет скачать файл из private Forgejo Release без пользовательского токена. Токен Forgejo нельзя вшивать в desktop-приложение.

Выбран второй безопасный вариант распространения:

- `timeweb/peeknook` остаётся приватным источником кода;
- отдельный публичный `releases/peeknook-releases` создан для подписанных updater-файлов;
- шаблон его безопасного содержимого лежит в `distribution/repobase-public/`;
- `scripts/peeknook-release-channel.py` проверяет адрес, разделение private/public и обязательное наличие платформ macOS/Windows в контракте.

В release-репозитории опубликованы только `README.md`, `SECURITY.md` и `channel.json`; исходного кода, пользовательских данных и секретов там нет. Репозиторий вынесен в отдельную публичную организацию `releases`, а рабочая организация `timeweb` остаётся приватной. Его ветка `main` защищена allowlist команды `Owners`, правило применяется к администраторам. Release-теги `v*` разрешены `Owners` и отдельной команде `Publishers`. Одноразовые административные PAT, использованные для создания и настройки, удалены.

Для автоматической публикации создан restricted-пользователь `peeknook-release-bot`: он не администратор, не видит приватный `timeweb/peeknook` и входит только в `Publishers`, привязанную к `releases/peeknook-releases`. Постоянный PAT имеет только scope `write:repository`; его значение через stdin записано в GitHub Actions Secret `REPOBASE_RELEASE_TOKEN` и не сохранено в checkout или локальном файле. Живой закрытый probe доказал, что бот может создать draft на защищённом `v*` tag; после проверки draft, tag и временный probe-PAT удалены.

Для первого настоящего релиза добавлен `scripts/peeknook-publish-repobase-release.py`. По умолчанию он ничего не загружает: проверяет совпадение версии и tag, наличие DMG, macOS updater-архива, MSI, Windows setup, обеих Tauri-подписей и точных RepoBase URL в `latest.json`. Публикация требует сразу трёх условий: флаг `--publish`, точное подтверждение `releases/peeknook-releases` и токен из `PEEKNOOK_REPOBASE_RELEASE_TOKEN`. Сначала создаётся невидимый draft; публичным он становится только после загрузки и сверки полного инвентаря. Существующий draft или отличающийся release автоматически не перезаписывается. Безопасный повтор CI допускается только для уже опубликованного релиза, у которого имена, размеры и SHA-256 всех скачанных файлов полностью совпали с локальным проверенным комплектом.

Временный GitHub workflow теперь собирает приложение уже с endpoint `https://repobase.ru/releases/peeknook-releases/releases/latest/download/latest.json`. ARM64 macOS runner закреплён на `macos-15`, x64 Windows runner — на `windows-2025`; перед сборкой дополнительно проверяется фактическая архитектура. После платформенной проверки workflow обязан сначала опубликовать RepoBase release. Только затем создаётся GitHub bridge-release с теми же подписанными файлами для старых установок. Это не возвращает исходный код на GitHub как источник истины: GitHub остаётся только временным поставщиком native runners и переходного download-канала.

Будущий endpoint зафиксирован как `https://repobase.ru/releases/peeknook-releases/releases/latest/download/latest.json`, но в установленном приложении он пока намеренно не включён. Старый `v0.2.7` смотрит на GitHub, поэтому потребуется один проверенный подписанный bridge-release по старому каналу, который установит версию с новым публичным endpoint.

13 августа 2026 года RepoBase переведён в режим, где публичные репозитории доступны без входа, а новые репозитории по умолчанию по-прежнему создаются приватными. Поскольку приватность организации Forgejo скрывает даже публичный дочерний репозиторий, канал вынесен из приватной `timeweb` в отдельную публичную организацию `releases`. Живая проверка без cookie и токена подтверждает ответы `200` для страницы, API и raw-файла канала; остальные приватные репозитории не должны становиться публичными. Адрес `releases/latest/download/latest.json` пока отвечает `404` по ожидаемой причине: настоящий релиз ещё не создан, поэтому анонимное скачивание реального release asset ещё не доказано.

## Следующий owner-gate

1. Добавить собственные Apple/Windows signing credentials в секреты временного native-build bridge. RepoBase release-бот и `REPOBASE_RELEASE_TOKEN` уже настроены; административный токен не используется.
2. Опубликовать первый настоящий подписанный релиз через fail-closed workflow, затем проверить `latest.json` и оба нативных файла без cookie и токена.
3. Выпустить подписанный bridge-release по старому GitHub-каналу только после проверки нового RepoBase endpoint.
4. Перед каждым source push запускать:

   ```bash
   ./scripts/peeknook-repobase-preflight.sh
   ```

5. Отправлять только конкретную ветку или конкретный tag. Не использовать `git push --mirror`, `--force` или массовый `--tags`.

Текущее состояние: `main` опубликована в RepoBase, локальная ветка отслеживает `repobase/main`, SSH-доступ подтверждён, пользовательская SQLite отсутствует во всей опубликованной истории. Публичный канал и изолированный publisher-бот готовы, но реальный подписанный release asset и переходный bridge-release ещё не выпущены из-за отсутствующих Apple/Windows credentials.
