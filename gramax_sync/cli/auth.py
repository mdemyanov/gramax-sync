"""Команды для управления аутентификацией."""

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

from gramax_sync.auth.token_manager import TokenManager

console = Console()


@click.group()
def auth() -> None:
    """Управление аутентификацией."""
    pass


@auth.command()
@click.option(
    "--url",
    help="URL GitLab инстанса (например, https://gitlab.example.com)",
    default=None,
)
@click.option(
    "--oauth",
    is_flag=True,
    default=False,
    help="Использовать OAuth аутентификацию через браузер",
)
@click.option(
    "--pat",
    is_flag=True,
    default=False,
    help="Использовать Personal Access Token",
)
@click.option(
    "--application-id",
    help="OAuth Application ID (или используйте переменную окружения GRAMAX_OAUTH_APPLICATION_ID)",
    default=None,
)
@click.option(
    "--application-secret",
    help="OAuth Application Secret (или используйте переменную окружение GRAMAX_OAUTH_APPLICATION_SECRET)",
    default=None,
)
def login(
    url: str | None,
    oauth: bool,
    pat: bool,
    application_id: str | None,
    application_secret: str | None,
) -> None:
    """Войти в систему (аутентификация)."""
    # Определяем URL GitLab
    if url is None:
        # Пытаемся получить из конфигурации
        try:
            from gramax_sync.config.config_manager import load_config

            config = load_config()
            if config:
                url = config.base_url
        except Exception:
            pass

        # Если всё ещё нет, запрашиваем у пользователя
        if url is None:
            url = Prompt.ask(
                "Введите URL GitLab инстанса",
                default="https://itsmf.gitlab.yandexcloud.net",
            )

    # Убираем trailing slash
    url = url.rstrip("/")

    # Определяем метод аутентификации
    if oauth and pat:
        console.print("[red]❌ Нельзя использовать --oauth и --pat одновременно[/red]")
        raise click.Abort()

    if not oauth and not pat:
        # Интерактивный выбор
        console.print("\n[cyan]Выберите метод аутентификации:[/cyan]")
        console.print("  1. OAuth (через браузер) — рекомендуется")
        console.print("  2. Personal Access Token (PAT)")

        choice = Prompt.ask(
            "Выберите метод",
            choices=["1", "2", "oauth", "pat"],
            default="1",
        )

        if choice in ("1", "oauth"):
            oauth = True
        else:
            pat = True

    # Выполняем аутентификацию
    try:
        if oauth:
            console.print(f"\n[cyan]Аутентификация через OAuth для {url}...[/cyan]")
            token = TokenManager.authenticate_via_oauth(
                url=url,
                application_id=application_id,
                application_secret=application_secret,
            )
            console.print(f"[green]✅ Аутентификация успешна![/green]")
        else:
            console.print(f"\n[cyan]Аутентификация через Personal Access Token для {url}...[/cyan]")
            token = TokenManager.prompt_for_token()
            TokenManager.save_token_with_type(url, token, "PAT")
            console.print(f"[green]✅ Токен сохранён![/green]")

    except ValueError as e:
        console.print(f"[red]❌ Ошибка аутентификации: {e}[/red]")
        raise click.Abort()
    except OSError as e:
        console.print(f"[red]❌ Ошибка: {e}[/red]")
        raise click.Abort()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Аутентификация отменена пользователем[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Неожиданная ошибка: {e}[/red]")
        raise click.Abort()


@auth.command()
@click.option(
    "--url",
    help="URL GitLab инстанса (если не указан, показываются все)",
    default=None,
)
@click.option(
    "--check-validity",
    is_flag=True,
    default=False,
    help="Проверить валидность токена через GitLab API",
)
@click.option(
    "--show-token",
    is_flag=True,
    default=False,
    help="Показать токен (первые и последние 4 символа)",
)
@click.option(
    "--show-scopes",
    is_flag=True,
    default=False,
    help="Показать права токена (scopes) через GitLab API",
)
def status(url: str | None, check_validity: bool, show_token: bool, show_scopes: bool) -> None:
    """Показать статус аутентификации."""
    console.print("\n[bold]🔐 Статус аутентификации[/bold]\n")

    # Если указан URL, показываем только для него
    if url:
        url = url.rstrip("/")
        token = TokenManager.get_token(url)
        token_type = TokenManager.get_token_type(url)

        if token:
            console.print(f"GitLab: [cyan]{url}[/cyan]")
            console.print(f"  [green]✓ Токен: {token_type or 'PAT'} (настроен)[/green]")
            
            # Показываем токен (первые и последние 4 символа), если запрошено
            if show_token:
                if len(token) > 8:
                    masked_token = f"{token[:4]}...{token[-4:]}"
                else:
                    masked_token = "****"
                console.print(f"  [dim]Токен: {masked_token}[/dim]")
            
            # Получаем информацию о токене через GitLab API, если запрошено
            if show_scopes or check_validity:
                try:
                    from gramax_sync.gitlab.client import GitLabClient
                    import gitlab.exceptions
                    import requests
                    import json
                    
                    client = GitLabClient(url=url, token=token)
                    
                    # Получаем информацию о пользователе
                    try:
                        gl = client._get_client()
                        try:
                            user = gl.user
                            console.print(f"  [dim]Пользователь: {user.username} ({user.name})[/dim]")
                            console.print(f"  [dim]Email: {user.email}[/dim]")
                        except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as user_error:
                            # Если не удалось получить через gl.user, используем прямой HTTP запрос
                            error_str = str(user_error).lower()
                            if "restobject" in error_str or "response" in error_str or "parsing" in error_str:
                                headers = {"PRIVATE-TOKEN": token}
                                user_response = requests.get(
                                    f"{url}/api/v4/user",
                                    headers=headers,
                                    timeout=10
                                )
                                if user_response.status_code == 200:
                                    user_data = user_response.json()
                                    console.print(f"  [dim]Пользователь: {user_data.get('username', 'N/A')} ({user_data.get('name', 'N/A')})[/dim]")
                                    console.print(f"  [dim]Email: {user_data.get('email', 'N/A')}[/dim]")
                                else:
                                    console.print(f"  [yellow]⚠️  Не удалось получить информацию о пользователе: HTTP {user_response.status_code}[/yellow]")
                            else:
                                raise
                    except Exception as e:
                        console.print(f"  [yellow]⚠️  Не удалось получить информацию о пользователе: {e}[/yellow]")
                    
                    # Показываем scopes, если запрошено
                    if show_scopes:
                        console.print("  [dim]Права токена (scopes):[/dim]")
                        console.print("  [dim]  Примечание: GitLab API не предоставляет информацию о scopes токена.[/dim]")
                        console.print("  [dim]  Проверьте права токена в GitLab: Settings → Access Tokens[/dim]")
                        console.print("  [dim]  Необходимые права: read_api, read_repository, read_user[/dim]")
                except Exception as e:
                    console.print(f"  [yellow]⚠️  Не удалось получить информацию о токене: {e}[/yellow]")

            # Проверяем валидность, если запрошено
            if check_validity:
                console.print("  [dim]Проверка валидности токена...[/dim]")
                is_valid, error_msg = TokenManager.check_token_validity(url)
                if is_valid:
                    console.print("  [green]✓ Токен валидный[/green]")
                else:
                    console.print(f"  [red]✗ Токен невалидный: {error_msg}[/red]")
                    console.print("  [yellow]💡 Запустите 'gramax-sync auth refresh' для обновления токена[/yellow]")
        else:
            console.print(f"GitLab: [cyan]{url}[/cyan]")
            console.print(f"  [red]✗ Токен не настроен[/red]")
    else:
        # Пытаемся получить из конфигурации
        try:
            from gramax_sync.config.config_manager import load_config

            config = load_config()
            if config:
                url = config.base_url
                token = TokenManager.get_token(url)
                token_type = TokenManager.get_token_type(url)

                console.print(f"GitLab: [cyan]{url}[/cyan]")
                if token:
                    console.print(f"  [green]✓ Токен: {token_type or 'PAT'} (настроен)[/green]")
                    
                    # Показываем токен (первые и последние 4 символа), если запрошено
                    if show_token:
                        if len(token) > 8:
                            masked_token = f"{token[:4]}...{token[-4:]}"
                        else:
                            masked_token = "****"
                        console.print(f"  [dim]Токен: {masked_token}[/dim]")
                    
                    # Получаем информацию о токене через GitLab API, если запрошено
                    if show_scopes or check_validity:
                        try:
                            from gramax_sync.gitlab.client import GitLabClient
                            import gitlab.exceptions
                            import requests
                            import json
                            
                            client = GitLabClient(url=url, token=token)
                            
                            # Получаем информацию о пользователе
                            try:
                                gl = client._get_client()
                                try:
                                    user = gl.user
                                    console.print(f"  [dim]Пользователь: {user.username} ({user.name})[/dim]")
                                    console.print(f"  [dim]Email: {user.email}[/dim]")
                                except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as user_error:
                                    # Если не удалось получить через gl.user, используем прямой HTTP запрос
                                    error_str = str(user_error).lower()
                                    if "restobject" in error_str or "response" in error_str or "parsing" in error_str:
                                        headers = {"PRIVATE-TOKEN": token}
                                        user_response = requests.get(
                                            f"{url}/api/v4/user",
                                            headers=headers,
                                            timeout=10
                                        )
                                        if user_response.status_code == 200:
                                            user_data = user_response.json()
                                            console.print(f"  [dim]Пользователь: {user_data.get('username', 'N/A')} ({user_data.get('name', 'N/A')})[/dim]")
                                            console.print(f"  [dim]Email: {user_data.get('email', 'N/A')}[/dim]")
                                        else:
                                            console.print(f"  [yellow]⚠️  Не удалось получить информацию о пользователе: HTTP {user_response.status_code}[/yellow]")
                                    else:
                                        raise
                            except Exception as e:
                                console.print(f"  [yellow]⚠️  Не удалось получить информацию о пользователе: {e}[/yellow]")
                            
                            # Показываем scopes, если запрошено
                            if show_scopes:
                                console.print("  [dim]Права токена (scopes):[/dim]")
                                console.print("  [dim]  Примечание: GitLab API не предоставляет информацию о scopes токена.[/dim]")
                                console.print("  [dim]  Проверьте права токена в GitLab: Settings → Access Tokens[/dim]")
                                console.print("  [dim]  Необходимые права: read_api, read_repository, read_user[/dim]")
                        except Exception as e:
                            console.print(f"  [yellow]⚠️  Не удалось получить информацию о токене: {e}[/yellow]")

                    # Проверяем валидность, если запрошено
                    if check_validity:
                        console.print("  [dim]Проверка валидности токена...[/dim]")
                        is_valid, error_msg = TokenManager.check_token_validity(url)
                        if is_valid:
                            console.print("  [green]✓ Токен валидный[/green]")
                        else:
                            console.print(f"  [red]✗ Токен невалидный: {error_msg}[/red]")
                            console.print("  [yellow]💡 Запустите 'gramax-sync auth refresh' для обновления токена[/yellow]")
                else:
                    console.print(f"  [red]✗ Токен не настроен[/red]")
            else:
                console.print("[yellow]⚠️  Конфигурация не найдена[/yellow]")
                console.print("[dim]Запустите 'gramax-sync init' для первоначальной настройки[/dim]")
        except Exception:
            console.print("[yellow]⚠️  Не удалось загрузить конфигурацию[/yellow]")


@auth.command()
@click.option(
    "--url",
    help="URL GitLab инстанса",
    required=True,
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Не запрашивать подтверждение",
)
def logout(url: str, yes: bool) -> None:
    """Выйти из системы (удалить токен)."""
    url = url.rstrip("/")

    # Проверяем, есть ли токен
    token = TokenManager.get_token(url)
    if not token:
        console.print(f"[yellow]⚠️  Токен для {url} не найден[/yellow]")
        return

    # Запрашиваем подтверждение
    if not yes:
        if not Confirm.ask(f"Удалить токен для {url}?"):
            console.print("[yellow]Отменено[/yellow]")
            return

    # Удаляем токен
    try:
        TokenManager.delete_token(url)
        # Также удаляем тип токена
        import keyring

        try:
            keyring.delete_password("gramax-sync", f"gitlab_token_type:{url}")
        except Exception:
            pass  # Игнорируем ошибки при удалении типа
        console.print(f"[green]✅ Токен для {url} удалён[/green]")
    except Exception as e:
        console.print(f"[red]❌ Ошибка при удалении токена: {e}[/red]")
        raise click.Abort()


@auth.command()
@click.option(
    "--url",
    help="URL GitLab инстанса",
    default=None,
)
@click.option(
    "--oauth",
    is_flag=True,
    default=False,
    help="Использовать OAuth для обновления токена",
)
@click.option(
    "--pat",
    is_flag=True,
    default=False,
    help="Использовать Personal Access Token для обновления",
)
@click.option(
    "--application-id",
    help="OAuth Application ID (для OAuth)",
    default=None,
)
@click.option(
    "--application-secret",
    help="OAuth Application Secret (для OAuth)",
    default=None,
)
def refresh(
    url: str | None,
    oauth: bool,
    pat: bool,
    application_id: str | None,
    application_secret: str | None,
) -> None:
    """Обновить токен (переаутентификация)."""
    # Определяем URL GitLab
    if url is None:
        # Пытаемся получить из конфигурации
        try:
            from gramax_sync.config.config_manager import load_config

            config = load_config()
            if config:
                url = config.base_url
        except Exception:
            pass

        # Если всё ещё нет, запрашиваем у пользователя
        if url is None:
            url = Prompt.ask(
                "Введите URL GitLab инстанса",
                default="https://itsmf.gitlab.yandexcloud.net",
            )

    url = url.rstrip("/")

    # Проверяем, есть ли токен
    existing_token = TokenManager.get_token(url)
    if not existing_token:
        console.print(f"[yellow]⚠️  Токен для {url} не найден[/yellow]")
        console.print("[cyan]Используйте 'gramax-sync auth login' для первоначальной аутентификации[/cyan]")
        return

    # Определяем метод обновления
    if oauth and pat:
        console.print("[red]❌ Нельзя использовать --oauth и --pat одновременно[/red]")
        raise click.Abort()

    use_oauth = oauth or (not pat and existing_token and TokenManager.get_token_type(url) == "OAuth")

    # Выполняем обновление токена
    try:
        if use_oauth:
            console.print(f"\n[cyan]Обновление токена через OAuth для {url}...[/cyan]")
            token = TokenManager.refresh_token(
                url=url,
                application_id=application_id,
                application_secret=application_secret,
                use_oauth=True,
            )
            console.print(f"[green]✅ Токен успешно обновлён![/green]")
        else:
            console.print(f"\n[cyan]Обновление токена через Personal Access Token для {url}...[/cyan]")
            token = TokenManager.refresh_token(
                url=url,
                use_oauth=False,
            )
            console.print(f"[green]✅ Токен успешно обновлён![/green]")

    except ValueError as e:
        console.print(f"[red]❌ Ошибка обновления токена: {e}[/red]")
        console.print("[yellow]💡 Попробуйте использовать 'gramax-sync auth login' для повторной аутентификации[/yellow]")
        raise click.Abort()
    except OSError as e:
        console.print(f"[red]❌ Ошибка: {e}[/red]")
        raise click.Abort()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Обновление токена отменено пользователем[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Неожиданная ошибка: {e}[/red]")
        raise click.Abort()

