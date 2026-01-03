# Настройка прав токена для gramax-sync

## Обзор

Для корректной работы `gramax-sync` требуется Personal Access Token (PAT) или OAuth токен с определёнными правами доступа к GitLab API. Этот документ описывает необходимые права и способы их настройки.

## Необходимые права токена

### Минимальные права (только чтение)

Для базовых операций чтения данных из GitLab требуются следующие права:

1. **`read_api`** ✅ **Обязательно**
   - Чтение данных через GitLab API
   - Получение информации о проектах
   - Получение списка проектов
   - Проверка доступа к репозиториям

2. **`read_repository`** ✅ **Обязательно**
   - Чтение содержимого репозиториев
   - Получение дерева файлов (`repository_tree`)
   - Чтение содержимого файлов (`files.get`)
   - Получение информации о ветках

3. **`read_user`** ✅ **Рекомендуется**
   - Получение информации о текущем пользователе
   - Проверка аутентификации
   - Валидация токена

### Дополнительные права (для расширенного функционала)

Если планируется использование дополнительных функций:

4. **`api`** ⚠️ **Опционально**
   - Полный доступ к API (включает `read_api`)
   - Может потребоваться для некоторых операций

## Операции, выполняемые приложением

### Операции чтения (требуют `read_api` и `read_repository`)

1. **Получение информации о проекте**
   ```python
   gl.projects.get(project_path)
   ```
   - Используется в: `check_repository_access()`, `get_project_info()`, `get_clone_url()`

2. **Получение дерева репозитория**
   ```python
   project.repository_tree(path="", ref=branch, recursive=True)
   ```
   - Используется в: `check_repository_access()` для поиска `workspace.yaml`

3. **Получение содержимого файлов**
   ```python
   project.files.get(file_path="workspace.yaml", ref=branch)
   ```
   - Используется в: `get_workspace_file()`, `get_file_content()`

4. **Получение списка проектов**
   ```python
   gl.projects.list(get_all=True)
   ```
   - Используется как альтернативный метод при ошибках с `projects.get()`

5. **Прямые HTTP запросы**
   ```python
   gl.http_get("/projects/{encoded_path}")
   gl.http_get("/projects/{encoded_path}/repository/tree")
   ```
   - Используются как fallback при проблемах с RESTObject

### Операции записи

⚠️ **Важно:** Приложение **НЕ выполняет** операции записи через GitLab API. Все операции commit/push выполняются через стандартные Git команды, которые используют HTTPS URL с токеном в качестве пароля.

## Создание токена с правильными правами

### Способ 1: Personal Access Token (PAT)

1. Войдите в GitLab
2. Перейдите в **Settings** → **Access Tokens** (или **User Settings** → **Access Tokens**)
3. Создайте новый токен со следующими параметрами:
   - **Token name**: `gramax-sync` (или любое другое имя)
   - **Expiration date**: Установите срок действия (рекомендуется не более 1 года)
   - **Select scopes**: Выберите следующие права:
     - ✅ `read_api`
     - ✅ `read_repository`
     - ✅ `read_user`
4. Нажмите **Create personal access token**
5. **Скопируйте токен** (он будет показан только один раз!)

### Способ 2: OAuth Application

Если используется OAuth аутентификация:

1. Перейдите в **Settings** → **Applications** (для администратора) или создайте OAuth Application
2. Настройте OAuth Application:
   - **Name**: `gramax-sync`
   - **Redirect URI**: `http://localhost:8765/callback`
   - **Scopes**: Выберите те же права, что и для PAT:
     - ✅ `read_api`
     - ✅ `read_repository`
     - ✅ `read_user`
3. Сохраните **Application ID** и **Application Secret**

## Проверка прав токена

### Через командную строку

```bash
# Проверка валидности токена
gramax-sync auth check

# Проверка с указанием URL
gramax-sync auth check --url https://itsmf.gitlab.yandexcloud.net
```

### Через GitLab API

Вы можете проверить права токена напрямую через API:

```bash
# Проверка текущего пользователя (требует read_user)
curl --header "PRIVATE-TOKEN: YOUR_TOKEN" \
  "https://itsmf.gitlab.yandexcloud.net/api/v4/user"

# Проверка доступа к проекту (требует read_api и read_repository)
curl --header "PRIVATE-TOKEN: YOUR_TOKEN" \
  "https://itsmf.gitlab.yandexcloud.net/api/v4/projects/ritm-authors%2Fgramax-yaml-manager"
```

## Типичные проблемы с правами

### Ошибка 403 (Forbidden)

**Симптомы:**
```
❌ Нет доступа к репозиторию: https://...
💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления
```

**Причины:**
- Токен не имеет права `read_repository`
- Токен не имеет права `read_api`
- Проект находится в приватной группе, к которой нет доступа

**Решение:**
1. Проверьте права токена в GitLab
2. Убедитесь, что токен имеет все необходимые права (`read_api`, `read_repository`, `read_user`)
3. Проверьте, что у пользователя есть доступ к проекту/группе
4. Создайте новый токен с правильными правами

### Ошибка 401 (Unauthorized)

**Симптомы:**
```
❌ Требуется аутентификация для доступа к репозиторию
💡 Запустите 'gramax-sync auth login' для аутентификации
```

**Причины:**
- Токен недействителен или истёк
- Токен не был передан в запросе
- Токен был удалён или отозван

**Решение:**
1. Проверьте, что токен сохранён: `gramax-sync auth check`
2. Если токен истёк, создайте новый: `gramax-sync auth login`
3. Убедитесь, что токен правильно сохранён в keyring

### Ошибка "Репозиторий не найден"

**Симптомы:**
```
❌ Репозиторий не найден: https://...
```

**Причины:**
- Неправильный URL репозитория
- Токен не имеет доступа к проекту (даже если проект существует)
- Проект находится в группе, к которой нет доступа

**Решение:**
1. Проверьте правильность URL репозитория
2. Убедитесь, что токен имеет право `read_api` и `read_repository`
3. Проверьте, что у пользователя есть доступ к группе/проекту в GitLab
4. Попробуйте получить доступ к проекту через веб-интерфейс GitLab

## Рекомендации по безопасности

1. **Минимальные права**: Используйте только необходимые права (`read_api`, `read_repository`, `read_user`)
2. **Срок действия**: Установите разумный срок действия токена (не более 1 года)
3. **Ротация токенов**: Регулярно обновляйте токены (каждые 3-6 месяцев)
4. **Хранение**: Токены хранятся в системном keyring, но убедитесь, что система защищена
5. **Не коммитьте токены**: Никогда не добавляйте токены в Git репозиторий

## Проверка прав через код

Приложение автоматически проверяет права при выполнении операций:

```python
# Пример проверки доступа
client = GitLabClient(url=url, token=token)
has_access, error = client.check_repository_access(repo_url, branch)
```

Если права недостаточны, вы получите `GitLabPermissionError` с описанием проблемы.

## Дополнительная информация

- [GitLab Personal Access Tokens Documentation](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)
- [GitLab OAuth Applications Documentation](https://docs.gitlab.com/ee/integration/oauth_provider.html)
- [GitLab API Scopes](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html#personal-access-token-scopes)

## Быстрая проверка

Выполните следующую команду для проверки всех настроек:

```bash
# 1. Проверка токена
gramax-sync auth check

# 2. Проверка доступа к репозиторию
gramax-sync init --repo-url https://itsmf.gitlab.yandexcloud.net/ritm-authors/gramax-yaml-manager

# 3. Если всё работает, вы увидите:
# ✅ Подключение установлено. Файл workspace.yaml найден.
```

Если все проверки прошли успешно, токен настроен правильно! 🎉

