# Настройка OAuth Application в GitLab

Это руководство поможет вам настроить OAuth Application в GitLab для использования с `gramax-sync`.

## Что такое OAuth Application?

OAuth Application позволяет `gramax-sync` получать доступ к GitLab API через браузерную авторизацию, без необходимости вручную создавать и вводить Personal Access Token.

## Шаги настройки

### 1. Создание OAuth Application в GitLab

Для GitLab Community Edition (`https://itsmf.gitlab.yandexcloud.net`):

1. **Войдите в GitLab** по адресу https://itsmf.gitlab.yandexcloud.net
2. **Перейдите в настройки пользователя:**
   - Нажмите на ваш аватар в правом верхнем углу
   - Выберите **Preferences** или **Settings**
3. **Откройте раздел Applications:**
   - В левом меню найдите **Applications** (или **OAuth Applications**)
   - Или перейдите напрямую: https://itsmf.gitlab.yandexcloud.net/-/profile/applications
4. **Создайте новое приложение:**
   - Нажмите **Add new application** (или **New application**)

### 2. Заполнение формы

Заполните следующие поля:

- **Name**: `gramax-sync` (или любое другое имя)
- **Redirect URI**: `http://localhost:8765/callback`
  - ⚠️ **Важно**: Этот URI должен точно совпадать с указанным выше
  - Если порт 8765 занят, `gramax-sync` автоматически найдёт доступный порт
- **Scopes** (права доступа):
  - ✅ `read_api` — чтение через API
  - ✅ `read_repository` — чтение репозиториев
  - ✅ `write_repository` — запись в репозитории (для commit/push)

### 3. Сохранение Application ID и Secret

После создания приложения вы получите:

- **Application ID** — публичный идентификатор приложения
- **Application Secret** — секретный ключ (только для confidential applications)

⚠️ **Важно**: Сохраните эти значения в безопасном месте!

### 4. Настройка в gramax-sync

Есть два способа указать Application ID:

#### Способ 1: Переменные окружения (рекомендуется)

```bash
export GRAMAX_OAUTH_APPLICATION_ID="your_application_id"
export GRAMAX_OAUTH_APPLICATION_SECRET="your_application_secret"  # опционально
```

#### Способ 2: Параметры команды

```bash
gramax-sync auth login --oauth \
  --url https://gitlab.example.com \
  --application-id your_application_id \
  --application-secret your_application_secret
```

## Использование

После настройки OAuth Application вы можете использовать OAuth аутентификацию:

```bash
# Интерактивный выбор метода
gramax-sync auth login --url https://gitlab.example.com

# Прямой вызов OAuth
gramax-sync auth login --oauth --url https://gitlab.example.com
```

## Типы OAuth Applications

### Public Application (рекомендуется для начала)

- Не требует Application Secret
- Подходит для локального использования
- Application ID достаточно для работы

### Confidential Application

- Требует Application Secret
- Более безопасно для production использования
- Secret должен храниться в переменных окружения

## Безопасность

1. **Application Secret**: Никогда не коммитьте Application Secret в репозиторий
2. **Redirect URI**: Убедитесь, что Redirect URI точно совпадает с указанным в приложении
3. **Scopes**: Предоставляйте только необходимые права доступа
4. **Переменные окружения**: Используйте переменные окружения для хранения секретов

## Troubleshooting

### Ошибка: "Client authentication failed due to unknown client"

**Причина**: Используется неверный или несуществующий Application ID (часто `test_app_id`).

**Решение**:
1. Проверьте переменную окружения:
   ```bash
   echo $GRAMAX_OAUTH_APPLICATION_ID
   ```
2. Если выводит пустую строку или `test_app_id`, значит переменная не установлена
3. Создайте OAuth Application в GitLab (см. Шаг 1 выше)
4. Установите Application ID (см. Шаг 2 выше)
5. Проверьте снова: `./scripts/check_oauth_config.sh`

### Ошибка: "Не указан OAuth Application ID"

**Решение**: Убедитесь, что вы указали Application ID через переменную окружения или параметр `--application-id`.

### Ошибка: "Порт занят"

**Решение**: `gramax-sync` автоматически найдёт доступный порт. Если проблема сохраняется, проверьте, что порт 8765 и соседние порты не заняты другими приложениями.

### Ошибка: "redirect_uri_mismatch"

**Решение**: Убедитесь, что Redirect URI в GitLab Application точно совпадает с `http://localhost:8765/callback`.

### Браузер не открывается автоматически

**Решение**: Скопируйте URL из консоли и откройте его вручную в браузере.

## Пример полной настройки для itsmf.gitlab.yandexcloud.net

### ⚠️ ВАЖНО: Без Application ID OAuth не будет работать!

Если вы видите ошибку **"Client authentication failed due to unknown client"**, это означает, что:
- Переменная `GRAMAX_OAUTH_APPLICATION_ID` не установлена
- Или используется неверный Application ID (например, `test_app_id`)

### Шаг 1: Создание OAuth Application в GitLab

1. **Откройте в браузере:**
   ```
   https://itsmf.gitlab.yandexcloud.net/-/profile/applications
   ```

2. **Нажмите "Add new application"** (или "New application")

3. **Заполните форму:**
   - **Name**: `gramax-sync` (или любое другое имя)
   - **Redirect URI**: `http://127.0.0.1:8765/callback` или `http://localhost:8765/callback`
     - ⚠️ **КРИТИЧЕСКИ ВАЖНО**: URI должен быть **точно** таким, без пробелов и лишних символов!
     - Примечание: `127.0.0.1` и `localhost` эквивалентны, но в коде используется `127.0.0.1`
   - **Scopes**: выберите все три чекбокса:
     - ✅ `read_api`
     - ✅ `read_repository`
     - ✅ `write_repository`

4. **Нажмите "Save application"**

5. **Скопируйте Application ID:**
   - После сохранения вы увидите **Application ID** — это длинная строка
   - Пример: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0`
   - ⚠️ **Сохраните его!** Он понадобится в следующем шаге

6. **Если создаёте Confidential Application:**
   - Также скопируйте **Application Secret**
   - ⚠️ **Сохраните его в безопасном месте!** Он показывается только один раз

### Шаг 2: Настройка переменных окружения

**⚠️ ОБЯЗАТЕЛЬНО:** Замените `ваш_application_id_из_gitlab` на реальный ID, который вы скопировали!

**Вариант A: Временно (только для текущей сессии терминала)**

```bash
# Установите Application ID
export GRAMAX_OAUTH_APPLICATION_ID="ваш_application_id_из_gitlab"

# Если используете Confidential Application, укажите также Secret:
export GRAMAX_OAUTH_APPLICATION_SECRET="ваш_secret_из_gitlab"
```

**Вариант B: Постоянно (рекомендуется)**

Добавьте в `~/.zshrc` (или `~/.bashrc`):

```bash
# Добавьте в конец файла ~/.zshrc
echo 'export GRAMAX_OAUTH_APPLICATION_ID="ваш_application_id_из_gitlab"' >> ~/.zshrc
echo 'export GRAMAX_OAUTH_APPLICATION_SECRET="ваш_secret_из_gitlab"' >> ~/.zshrc  # опционально

# Примените изменения
source ~/.zshrc
```

**Вариант C: Автоматическая настройка (самый простой способ)**

```bash
./scripts/setup_oauth.sh
```

Скрипт проведёт вас через все шаги автоматически.

**Проверка:**

```bash
# Проверьте, что переменная установлена
echo $GRAMAX_OAUTH_APPLICATION_ID

# Должно вывести ваш Application ID (НЕ test_app_id!)
```

### Шаг 3: Выполнение аутентификации

```bash
# Выполните OAuth аутентификацию
gramax-sync auth login --oauth --url https://itsmf.gitlab.yandexcloud.net

# Или интерактивно (выберите OAuth)
gramax-sync auth login --url https://itsmf.gitlab.yandexcloud.net
```

### Шаг 4: Проверка статуса

```bash
# Проверьте, что аутентификация прошла успешно
gramax-sync auth status
```

### Важно!

⚠️ **Application ID обязателен!** Без него OAuth не будет работать. Убедитесь, что:
- Application ID скопирован правильно (без пробелов)
- Переменная окружения установлена перед запуском команды
- Redirect URI в GitLab точно совпадает с `http://localhost:8765/callback`

## Дополнительная информация

- [GitLab OAuth Documentation](https://docs.gitlab.com/ee/api/oauth2.html)
- [OAuth 2.0 Specification](https://oauth.net/2/)

