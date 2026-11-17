"""Module: Profile (SB-PR-*)."""

import pytest

from pages import ProfilePage
from test_data import messages as msg
from test_data import profile as data
from test_data.users import STANDARD_USER

pytestmark = pytest.mark.profile


@pytest.fixture
def profile_page(login_as, driver, base_url) -> ProfilePage:
    login_as(STANDARD_USER.username, STANDARD_USER.password)
    return ProfilePage(driver, base_url).open()


@pytest.mark.testcase("SB-PR-01")
def test_update_profile_with_valid_data(profile_page):
    page = profile_page
    assert page.values()["full_name"] == STANDARD_USER.full_name

    page.update(**data.UPDATED_PROFILE)

    assert page.success_text(msg.PROFILE_UPDATED) == msg.PROFILE_UPDATED
    assert page.wait_text_equals(ProfilePage.USER_FULL_NAME, data.UPDATED_PROFILE["full_name"]) == \
        data.UPDATED_PROFILE["full_name"]

    page.reload()
    saved = page.values()
    for field, value in data.UPDATED_PROFILE.items():
        assert saved[field] == value, f"{field} not persisted after reload"
    assert page.user_full_name == data.UPDATED_PROFILE["full_name"]
    assert page.current_username == STANDARD_USER.username, "Username must not change"


@pytest.mark.testcase("SB-PR-02")
def test_invalid_email_rejected(profile_page):
    page = profile_page
    page.update(email=data.INVALID_EMAIL)

    assert page.error_text("email", msg.EMAIL_INVALID) == msg.EMAIL_INVALID
    assert not page.is_success_shown()

    page.reload()
    assert page.values()["email"] == STANDARD_USER.email, "Invalid email must not be saved"


@pytest.mark.testcase("SB-PR-03")
def test_required_fields_blank(profile_page):
    page = profile_page
    page.update(full_name="", email="", phone="")

    expected = {
        "full_name": msg.FULL_NAME_REQUIRED,
        "email": msg.EMAIL_REQUIRED,
        "phone": msg.PHONE_REQUIRED,
    }
    actual = {field: page.error_text(field, text) for field, text in expected.items()}
    assert actual == expected
    assert not page.is_success_shown()
    assert page.user_full_name == STANDARD_USER.full_name
