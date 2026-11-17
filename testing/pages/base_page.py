"""Shared base for every SecureBank page object.

All waiting is explicit (WebDriverWait + expected_conditions); the driver runs with an
implicit wait of 0 and nothing in the suite calls time.sleep().
"""

from __future__ import annotations

import os
import sys

from selenium.common.exceptions import (
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

Locator = tuple[str, str]

DEFAULT_TIMEOUT = float(os.getenv("EXPLICIT_WAIT", "10"))
# Hydration of a Next.js page can be slow on a cold dev server; it is a soft wait.
HYDRATION_TIMEOUT = float(os.getenv("HYDRATION_WAIT", "15"))

_SELECT_ALL = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL

_IS_HYDRATED_JS = (
    "return Object.keys(arguments[0]).some(k => k.startsWith('__reactProps$'));"
)


def describe(locator: Locator) -> str:
    by, value = locator
    return f"#{value}" if by == By.ID else value


class BasePage:
    """Explicit-wait helpers shared by all pages."""

    PATH = "/"
    TITLE = ""
    # Element that only becomes interactive once React has hydrated the page.
    READY_ELEMENT: Locator | None = None

    def __init__(self, driver: WebDriver, base_url: str | None = None, timeout: float = DEFAULT_TIMEOUT):
        self.driver = driver
        self.base_url = (base_url or os.getenv("BASE_URL", "http://localhost:3000")).rstrip("/")
        self.timeout = timeout

    # ── navigation ───────────────────────────────────────────────────────────
    def url_for(self, path: str | None = None) -> str:
        return f"{self.base_url}{path if path is not None else self.PATH}"

    def open(self, path: str | None = None):
        self.driver.get(self.url_for(path))
        return self.wait_until_loaded()

    def wait_until_loaded(self):
        """Override per page; by default waits for READY_ELEMENT and hydration."""
        if self.READY_ELEMENT:
            self.wait_visible(self.READY_ELEMENT)
            self.wait_hydrated(self.READY_ELEMENT)
        return self

    def reload(self):
        self.driver.refresh()
        return self.wait_until_loaded()

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    @property
    def title(self) -> str:
        return self.driver.title

    def wait_url_contains(self, fragment: str, timeout: float | None = None) -> str:
        self._wait(timeout).until(
            EC.url_contains(fragment),
            f"URL did not contain '{fragment}' (current: {self.driver.current_url})",
        )
        return self.driver.current_url

    def wait_title(self, title: str, timeout: float | None = None) -> str:
        try:
            self._wait(timeout).until(EC.title_is(title))
        except TimeoutException:
            pass  # caller asserts on the returned value for a readable diff
        return self.driver.title

    # ── waits ────────────────────────────────────────────────────────────────
    def _wait(self, timeout: float | None = None) -> WebDriverWait:
        return WebDriverWait(
            self.driver,
            self.timeout if timeout is None else timeout,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    def wait_present(self, locator: Locator, timeout: float | None = None) -> WebElement:
        return self._wait(timeout).until(
            EC.presence_of_element_located(locator),
            f"Element {describe(locator)} was not present within {timeout or self.timeout}s",
        )

    def wait_visible(self, locator: Locator, timeout: float | None = None) -> WebElement:
        return self._wait(timeout).until(
            EC.visibility_of_element_located(locator),
            f"Element {describe(locator)} was not visible within {timeout or self.timeout}s",
        )

    def wait_all_visible(self, locator: Locator, timeout: float | None = None) -> list[WebElement]:
        return self._wait(timeout).until(
            EC.visibility_of_all_elements_located(locator),
            f"No visible elements matched {describe(locator)} within {timeout or self.timeout}s",
        )

    def wait_clickable(self, locator: Locator, timeout: float | None = None) -> WebElement:
        return self._wait(timeout).until(
            EC.element_to_be_clickable(locator),
            f"Element {describe(locator)} was not clickable within {timeout or self.timeout}s",
        )

    def wait_invisible(self, locator: Locator, timeout: float | None = None) -> bool:
        """True once the element is hidden or absent from the DOM."""
        return self._wait(timeout).until(
            EC.invisibility_of_element_located(locator),
            f"Element {describe(locator)} was still visible after {timeout or self.timeout}s",
        )

    def wait_hydrated(self, locator: Locator, timeout: float = HYDRATION_TIMEOUT) -> bool:
        """Soft-wait until React has attached its props to the element.

        Interacting with a server-rendered Next.js form before hydration can trigger a
        native (non-React) submit, so form pages wait for this before typing. Returns
        False instead of raising on timeout; the subsequent assertions will fail loudly
        if the page is genuinely broken.
        """

        def hydrated(driver):
            try:
                el = driver.find_element(*locator)
                return bool(driver.execute_script(_IS_HYDRATED_JS, el))
            except (NoSuchElementException, StaleElementReferenceException, JavascriptException):
                return False

        try:
            self._wait(timeout).until(hydrated)
            return True
        except TimeoutException:
            return False

    def wait_text_equals(self, locator: Locator, expected: str, timeout: float | None = None) -> str:
        """Wait for the element to be visible and show `expected`; return its actual text.

        Never raises on a text mismatch (only if the element never becomes visible), so
        the caller's `assert actual == expected` shows a precise diff.
        """
        self.wait_visible(locator, timeout)

        def matches(driver):
            try:
                return driver.find_element(*locator).text.strip() == expected
            except StaleElementReferenceException:
                return False

        try:
            self._wait(timeout).until(matches)
        except TimeoutException:
            pass
        return self.text_of(locator)

    def wait_text_contains(self, locator: Locator, fragment: str, timeout: float | None = None) -> str:
        self.wait_visible(locator, timeout)
        try:
            self._wait(timeout).until(EC.text_to_be_present_in_element(locator, fragment))
        except TimeoutException:
            pass
        return self.text_of(locator)

    def wait_attribute_equals(self, locator: Locator, name: str, expected: str, timeout: float | None = None) -> str | None:
        """Wait for an attribute to take a value; return its actual value."""
        self.wait_present(locator, timeout)
        try:
            self._wait(timeout).until(EC.text_to_be_present_in_element_attribute(locator, name, expected))
        except TimeoutException:
            pass
        return self.attribute_of(locator, name)

    # ── element actions ──────────────────────────────────────────────────────
    def find(self, locator: Locator) -> WebElement:
        return self.wait_present(locator)

    def find_all(self, locator: Locator) -> list[WebElement]:
        return self.driver.find_elements(*locator)

    def click(self, locator: Locator) -> None:
        self.wait_clickable(locator).click()

    def type(self, locator: Locator, value: str | int | float | None) -> None:
        """Replace the field's content with `value` (empty/None just clears it).

        Uses select-all + backspace instead of WebElement.clear(), because clear() does
        not fire the input event React controlled inputs listen to.
        """
        el = self.wait_visible(locator)
        el.click()
        el.send_keys(_SELECT_ALL, "a")
        el.send_keys(Keys.BACKSPACE)
        if value is not None and str(value) != "":
            el.send_keys(str(value))

    def select_by_value(self, locator: Locator, value: str) -> None:
        """Choose an option of a native <select>, waiting for it to be rendered."""
        self.wait_visible(locator)
        option = (By.CSS_SELECTOR, f"#{locator[1]} option[value='{value}']") if locator[0] == By.ID else None
        if option:
            self.wait_present(option)
        Select(self.find(locator)).select_by_value(value)

    def selected_value(self, locator: Locator) -> str:
        return Select(self.find(locator)).first_selected_option.get_attribute("value") or ""

    def option_values(self, locator: Locator) -> list[str]:
        return [o.get_attribute("value") or "" for o in Select(self.find(locator)).options]

    def text_of(self, locator: Locator) -> str:
        return self.find(locator).text.strip()

    def value_of(self, locator: Locator) -> str:
        return self.find(locator).get_attribute("value") or ""

    def attribute_of(self, locator: Locator, name: str) -> str | None:
        return self.find(locator).get_attribute(name)

    def cents_of(self, locator: Locator) -> int:
        raw = self.attribute_of(locator, "data-cents")
        assert raw is not None, f"{describe(locator)} has no data-cents attribute"
        return int(raw)

    def is_visible(self, locator: Locator) -> bool:
        els = self.driver.find_elements(*locator)
        return bool(els) and els[0].is_displayed()

    def is_enabled(self, locator: Locator) -> bool:
        return self.find(locator).is_enabled()
