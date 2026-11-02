"""Set a user's password from the laptop. Never prints the password.

Usage: python -m scripts.set_password <username>
"""

import getpass
import sys

from app.core.db import SessionLocal
from app.services.users import set_password_for_username


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.set_password <username>", file=sys.stderr)
        sys.exit(2)
    username = sys.argv[1]
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Again: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        sys.exit(1)
    with SessionLocal() as db:
        try:
            updated = set_password_for_username(db, username, password)
        except LookupError:
            print("User not found.", file=sys.stderr)
            sys.exit(1)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
    print(f"Password updated for {updated}.")


if __name__ == "__main__":
    main()
