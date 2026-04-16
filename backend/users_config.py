"""Demo user accounts (passwords in plain text for FYP only — use a real user store in production)."""

# Roles: Admin (full control), Investigator (assigned cases), Member (own cases only).
USERS = {
    "admin": {"password": "admin123", "role": "Admin", "name": "Admin User"},
    "investigator": {
        "password": "inv123",
        "role": "Investigator",
        "name": "Ali Investigator",
    },
    "analyst": {"password": "analyst123", "role": "Analyst", "name": "Sara Analyst"},
    # Member: basic user — request cases, view own case progress only
    "member": {"password": "member123", "role": "Member", "name": "Case Member"},
}


def all_usernames():
    return sorted(USERS.keys())
