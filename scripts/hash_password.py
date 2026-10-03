"""
scripts/hash_password.py
Generate a bcrypt password hash for use in the ADMIN_PASSWORD_HASH environment variable.

Usage:
    python scripts/hash_password.py

Then copy the output hash into your .env file:
    ADMIN_PASSWORD_HASH=<output>
"""

import getpass

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt not installed. Run: pip install bcrypt")
    raise SystemExit(1)


def main():
    print("=" * 50)
    print("  Think4U Launch Page — Admin Password Setup")
    print("=" * 50)
    print()

    password = getpass.getpass("Enter the admin password: ")
    if not password:
        print("ERROR: Password cannot be empty.")
        raise SystemExit(1)

    confirm = getpass.getpass("Confirm the admin password: ")
    if password != confirm:
        print("ERROR: Passwords do not match.")
        raise SystemExit(1)

    if len(password) < 8:
        print("WARNING: Password is very short. Use at least 12 characters for security.")

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    hash_str = hashed.decode("utf-8")

    print()
    print("✅ Password hash generated successfully!")
    print()
    print("Add this to your .env file:")
    print(f"ADMIN_PASSWORD_HASH={hash_str}")
    print()
    print("Keep this value secret. Never commit your .env file to version control.")


if __name__ == "__main__":
    main()
