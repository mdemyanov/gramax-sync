---
task: gramax-sync CLI
status: draft
priority: high
created: 2025-12-30
---

# gramax-sync — CLI для управления репозиториями РИТМ

## Цель

Создать консольный инструмент для синхронизации и управления множеством Git-репозиториев, определённых в конфигурационном файле `workspace.yaml` проекта РИТМ (Gramax).

## Контекст

РИТМ — методология управления ИТ с документацией в Gramax. Документация разбита на ~50 Git-репозиториев, структурированных по секциям. Ручная синхронизация неудобна — нужен инструмент для массовых операций clone/pull/commit/push.

## Требования

### Must have (Phase 1 — MVP)
- [ ] Парсинг `workspace.yaml` с Pydantic-валидацией
- [ ] Команда `clone` — клонирование всех репозиториев по секциям
- [ ] Команда `status` — статус всех репозиториев (modified/ahead/clean)
- [ ] Команда `pull` — обновление репозиториев
- [ ] Структура директорий: `{workspace_dir}/{section}/{catalog}/`
- [ ] Красивый вывод через Rich

### Should have (Phase 2)
- [ ] Команда `commit` с автогенерацией сообщений
- [ ] Команда `push`
- [ ] Команда `sync` (pull + commit + push)
- [ ] Фильтрация по `--section` и `--catalog` (glob patterns)

### Phase 3
- [ ] OAuth аутентификация через браузер
- [ ] Конфигурационный файл `~/.config/gramax-sync/config.yaml`
- [ ] Keyring интеграция для токенов

### Phase 4
- [ ] MCP server для Claude Desktop (7 tools)

### Won't have (в этой итерации)
- Параллельное клонирование
- GUI интерфейс
- Поддержка GitHub/Bitbucket (только GitLab)

## Технический контекст

- **Язык:** Python 3.10+
- **CLI framework:** Click
- **Git:** GitPython
- **Output:** Rich
- **Validation:** Pydantic
- **MCP:** fastmcp
- **Целевая платформа:** macOS (primary), Linux, Windows

## Ограничения

- Fail-fast при ошибках с подробной диагностикой
- Ветка по умолчанию: `private`
- URL репозитория: `{source.url}/ritm-authors/{catalog}`

## Референсы

- `references/spec.md` — полная спецификация с примерами CLI, моделями данных, MCP tools
- `assets/workspace.yaml` — пример конфигурационного файла

## Acceptance Criteria

```
GIVEN workspace.yaml с секциями и каталогами
WHEN пользователь выполняет `gramax-sync clone`
THEN создаётся структура {workspace_dir}/{section}/{catalog}/ 
     и все репозитории клонированы с веткой private

GIVEN склонированные репозитории с изменениями
WHEN пользователь выполняет `gramax-sync status`
THEN выводится список репозиториев с их статусом (clean/modified/ahead)

GIVEN репозитории с unpushed commits
WHEN пользователь выполняет `gramax-sync push`
THEN все изменения отправлены в remote
```

## CLI интерфейс

```bash
gramax-sync clone                    # Все репозитории
gramax-sync clone --section 1-*      # По паттерну секции
gramax-sync pull                     # Обновить все
gramax-sync status                   # Статус всех
gramax-sync commit -m "message"      # Закоммитить с изменениями
gramax-sync push                     # Отправить в remote
gramax-sync sync                     # pull + commit + push
```

## Примечания

- Полная спецификация в `references/spec.md` (~400 строк)
- Реализовывать поэтапно: Phase 1 → Phase 2 → Phase 3 → Phase 4
