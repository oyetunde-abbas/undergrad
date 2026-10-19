"""
One-time script: creates 3 ready-to-use beta test accounts directly in the
database, so testers can log in immediately without going through the
signup form themselves.

Safe to re-run — skips any account that already exists rather than erroring
or duplicating.

Run this AFTER the migration scripts (needs the users table to exist).
"""

from dotenv import load_dotenv
load_dotenv()

from auth_utils import hash_password
from db import create_user, get_user_by_email

BETA_ACCOUNTS = [
    {"email": "beta1@undergrad.test", "password": "Tns90FAxX2"},
    {"email": "beta2@undergrad.test", "password": "vZCmNratcA"},
    {"email": "beta3@undergrad.test", "password": "VK3OAKqEIa"},
]


def main():
    for account in BETA_ACCOUNTS:
        existing = get_user_by_email(account["email"])
        if existing:
            print(f"Already exists, skipping: {account['email']}")
            continue

        user_id = create_user(account["email"], hash_password(account["password"]))
        print(f"Created user #{user_id}: {account['email']}")

    print("\nBeta accounts ready. Credentials:")
    for account in BETA_ACCOUNTS:
        print(f"  {account['email']}  /  {account['password']}")


if __name__ == "__main__":
    main()
