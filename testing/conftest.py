"""Shared fixtures and configuration for the SecureBank Selenium suite.

Environment variables (all optional):
    BASE_URL            app under test (default http://localhost:3000)
    HEADLESS            1/0 — run Chrome headless (default 1)
    WINDOW_SIZE         browser size WIDTHxHEIGHT (default 1440x900)
    BROWSER             only "chrome" is supported (default chrome)
    CHROME_BINARY       custom Chrome executable (default: Selenium Manager discovery)
    EXPLICIT_WAIT       default explicit-wait timeout in seconds (default 10)
    PAGE_LOAD_TIMEOUT   driver page-load timeout in seconds (default 60)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

from pages import DashboardPage, LoginPage, RegisterPage
from test_data.customers import Customer
from utils.results_plugin import PLUGIN_NAME, ResultsPlugin, env_flag

TESTING_DIR = Path(__file__).resolve().parent
REPORTS_DIR = TESTING_DIR / "reports"
CATALOGUE = TESTING_DIR / "test_cases.json"


def _load_dotenv(path: Path = TESTING_DIR.parent / ".env") -> None:
    """Load the repo-root .env (if any); real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value and not os.environ.get(key.strip()):
                os.environ[key.strip()] = value


_load_dotenv()

BASE_URL =os.getenv("BASE_URL", "http://localhost:3000").rstrip("/")
HEADLESS = env_flag("HEADLESS", True)
BROWSER = os.getenv("BROWSER", "chrome").strip().lower()
PAGE_LOAD_TIMEOUT = float(os.getenv("PAGE_LOAD_TIMEOUT", "60"))


def _window_size() -> tuple[int, int]:
    raw = os.getenv("WINDOW_SIZE", "1440x900").lower().replace(",", "x")
    width, height = (int(part) for part in raw.split("x", 1))
    return width, height


# ── pytest configuration ─────────────────────────────────────────────────────
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config):
    # Anchor relative report paths (from pytest.ini) to testing/, so the reports land in
    # testing/reports/ whether pytest is started from testing/ or from the repo root.
    for option in ("xmlpath", "htmlpath"):
        value = getattr(config.option, option, None)
        if value and not os.path.isabs(value):
            setattr(config.option, option, str(TESTING_DIR / value))

    if BROWSER != "chrome":
        raise pytest.UsageError(f"BROWSER={BROWSER!r} is not supported; only 'chrome' is.")

    if not hasattr(config, "workerinput") and not config.pluginmanager.has_plugin(PLUGIN_NAME):
        config.pluginmanager.register(
            ResultsPlugin(config, TESTING_DIR, REPORTS_DIR, CATALOGUE), PLUGIN_NAME
        )


@pytest.hookimpl(optionalhook=True)
def pytest_metadata(metadata, config):
    plugin = config.pluginmanager.get_plugin(PLUGIN_NAME)
    metadata["Base URL"] = BASE_URL
    metadata["Headless"] = str(HEADLESS)
    if plugin is not None:
        metadata["Commit"] = plugin.meta.get("commit_sha") or "unknown"
        metadata["Branch"] = plugin.meta.get("branch") or "unknown"
        metadata["Trigger"] = plugin.meta.get("trigger")
        if plugin.meta.get("workflow_run_url"):
            metadata["Workflow run"] = plugin.meta["workflow_run_url"]


# ── fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def app_available(base_url):
    """Fail fast (one clear message per test) when the app is not running."""
    try:
        requests.get(f"{base_url}/bank/login", timeout=30)
    except requests.RequestException as exc:
        pytest.fail(f"SecureBank is not reachable at {base_url}: {exc}", pytrace=False)
    return base_url


def _chrome_options() -> ChromeOptions:
    width, height = _window_size()
    options = ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-search-engine-choice-screen")
    options.add_argument("--lang=en-US")
    # Keep Chrome's password manager / breach warnings from covering the page.
    options.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
            "intl.accept_languages": "en-US,en",
        },
    )
    if os.getenv("CHROME_BINARY"):
        options.binary_location = os.environ["CHROME_BINARY"]
    return options


@pytest.fixture
def driver(request, app_available):
    """A fresh Chrome per test = fresh localStorage/sessionStorage = freshly seeded bank."""
    drv = webdriver.Chrome(options=_chrome_options())  # Selenium Manager resolves chromedriver
    drv.implicitly_wait(0)
    drv.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    if not HEADLESS:
        drv.set_window_size(*_window_size())

    plugin = request.config.pluginmanager.get_plugin(PLUGIN_NAME)
    if plugin is not None and plugin.browser is None:
        caps = drv.capabilities
        plugin.browser = f"{caps.get('browserName', 'chrome')} {caps.get('browserVersion', '')}".strip()

    request.node.banktest_driver = drv  # lets the results plugin screenshot setup failures too
    yield drv
    drv.quit()


@pytest.fixture
def login_page(driver, base_url) -> LoginPage:
    return LoginPage(driver, base_url).open()


@pytest.fixture
def login_as(driver, base_url):
    """Factory: log in with (username, password) and return the loaded DashboardPage."""

    def _login(username: str, password: str) -> DashboardPage:
        return LoginPage(driver, base_url).open().login(username, password)

    return _login


@pytest.fixture
def register_customer(driver, base_url):
    """Factory: register a customer through the UI and return the new account number.

    Registration logs the new customer in; by default the helper then logs out so the
    next registration/login starts from a clean session.
    """

    def _register(customer: Customer, logout: bool = True) -> str:
        page = RegisterPage(driver, base_url).open()
        page.register(customer.full_name, customer.email, customer.password, customer.initial_deposit)
        page.wait_for_success()
        account_number = page.new_account_number
        if logout:
            DashboardPage(driver, base_url).open().logout()
        return account_number

    return _register
