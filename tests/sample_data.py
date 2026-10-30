"""Example LLM replies used by several tests."""
import json

VALID_SUITE = {
    "feature": "User login",
    "test_cases": [
        {
            "title": "Login with valid credentials",
            "requirement": "LOG-01",
            "type": "Positive",
            "priority": "High",
            "preconditions": "User is registered",
            "steps": ["Open the login page", "Enter valid email and password", "Click Login"],
            "test_data": "user@test.com / Passw0rd!",
            "expected_result": "User is taken to the home page",
        },
        {
            "title": "Login with wrong password",
            "requirement": "LOG-02",
            "type": "negative",          # lower case on purpose: must be normalised
            "priority": "HIGH",
            "preconditions": "User is registered",
            "steps": "1. Open the login page\n2. Enter a wrong password\n3. Click Login",  # a string on purpose
            "test_data": "user@test.com / wrong123",
            "expected_result": "Message 'Invalid email or password' is shown",
        },
        {
            "title": "Account locks after 5 failed attempts",
            "requirement": "LOG-03",
            "type": "Boundary",
            "priority": "Medium",
            "steps": ["Enter a wrong password 5 times", "Try a 6th login with the right password"],
            "expected_result": "Account is locked for 15 minutes",
        },
        {
            "title": "login with valid credentials",   # duplicate title: must be removed
            "requirement": "LOG-01",
            "type": "Positive",
            "priority": "High",
            "steps": ["Repeat of first case"],
            "expected_result": "Home page",
        },
    ],
}

VALID_REPLY = json.dumps(VALID_SUITE)
FENCED_REPLY = "Here are your test cases:\n```json\n" + VALID_REPLY + "\n```\nHope this helps!"

SCRIPT_REPLY = '''Sure! Here is the script:
```python
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:3000"


def test_login_with_valid_credentials(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.get_by_label("Email").fill("user@test.com")
    page.get_by_label("Password").fill("Passw0rd!")
    page.get_by_role("button", name="Login").click()
    expect(page).to_have_url(f"{BASE_URL}/home")
```
'''
