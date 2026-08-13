# PeekNook в Microsoft Store без покупки Windows-сертификата

## Короткий ответ

Это возможно только через **MSIX и Microsoft Store**. Мы отправляем в Partner
Center неподписанный MSIX, Microsoft проверяет приложение и подписывает принятую
сборку своим сертификатом. Пользователь устанавливает и обновляет PeekNook через
Store без предупреждения SmartScreen.

Это не отменяет подпись для обычных файлов `setup.exe` и `.msi`: Microsoft не
переподписывает такие установщики. Для прямого скачивания с RepoBase им по-прежнему
нужен настоящий Authenticode-сертификат.

## Что уже подготовлено в проекте

Отдельный ручной workflow `PeekNook Windows Store MSIX QA` на настоящем Windows
runner:

1. собирает Python backend как `peeknook-api.exe`;
2. проверяет API, локальную базу, CORS и корректное завершение процессов;
3. собирает Tauri-приложение без EXE/MSI installer и без Tauri updater;
4. складывает `PeekNook.exe`, sidecar и Store-иконки в MSIX;
5. распаковывает готовый MSIX и сверяет хэши обоих исполняемых файлов;
6. публикует только закрытый QA-артефакт GitHub Actions, но не отправляет его в Store.

QA-пакет имеет вымышленную identity `ai.peeknook.desktop.qa` и пометку
`QA-UNSIGNED`. Его нельзя отдавать пользователям или загружать в Partner Center.

Store-сборка также скрывает кнопку самостоятельного обновления PeekNook. Для неё
обновления устанавливает Microsoft Store. Обычная RepoBase-сборка продолжает
использовать отдельный Tauri updater-контракт.

## Что должен один раз сделать владелец

1. Войти или зарегистрироваться в [Partner Center](https://partner.microsoft.com/dashboard).
2. Создать продукт типа **MSIX or PWA app** и зарезервировать название PeekNook.
3. На странице Product identity скопировать без изменений:
   - Package/Identity/Name;
   - Package/Identity/Publisher;
   - Publisher display name.
4. Передать эти три значения сборочному скрипту и явно подтвердить, что они взяты
   из Partner Center.
5. Загрузить полученный `.msix` в черновик submission, заполнить описание,
   возрастной рейтинг, политику конфиденциальности и скриншоты.
6. Сначала отправить пакет в закрытый тестовый flight и проверить установку,
   запуск backend, создание блокнота, импорт PDF, перезапуск и обновление.
7. Только после успешного теста отправить submission на сертификацию и публикацию.

Пример команды на Windows после сборки приложения:

```powershell
pwsh scripts/peeknook-build-windows-store-msix.ps1 `
  -Mode PartnerCenter `
  -IdentityName "ТОЧНОЕ_PACKAGE_IDENTITY_NAME" `
  -Publisher "ТОЧНЫЙ_CN_ИЗ_PARTNER_CENTER" `
  -PublisherDisplayName "ТОЧНОЕ_ИМЯ_ИЗ_PARTNER_CENTER" `
  -ConfirmPartnerCenterIdentity
```

Скрипт намеренно не подписывает пакет и запрещает PartnerCenter-режим без явного
подтверждения identity. Полученный MSIX разрешено загружать только в Partner
Center: напрямую он не предназначен для установки, потому что подпись появится
после сертификации Microsoft.

## Что остаётся внешним блокером

- учётная запись разработчика Microsoft и зарезервированное название;
- точные Partner Center identity-значения;
- успешная автоматическая проверка MSIX на Windows runner;
- реальный закрытый flight и ручной пользовательский тест;
- политика конфиденциальности, Store-тексты, скриншоты и решение владельца о
  публикации.

Ни один из этих шагов нельзя честно заменить тестовым сертификатом или значениями,
придуманными в коде.
