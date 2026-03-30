"""
main.py - Entry point for the Python Quiz Application.
Handles user login and dashboard menu routing.
Automatically logs the user out when the terminal session ends (SIGHUP).
"""

import atexit
import getpass
import hashlib
import hmac
import json
import os
import re
import signal
import sys

USERS_FILE = "users.json"
_SALT_BYTES = 32  # bytes of entropy for each user's password salt


# ---------------------------------------------------------------------------
# User store helpers
# ---------------------------------------------------------------------------

def _load_users():
    """Return the users dict from disk, or an empty dict if none exists."""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️  Warning: Users file is corrupted. Starting with an empty user store.")
        return {}


def _save_users(users):
    """Persist the users dict to disk."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _hash_password(password, salt=None):
    """
    Return (salt, hash) using PBKDF2-HMAC-SHA256.
    If *salt* is None a new random salt is generated.
    """
    if salt is None:
        salt = os.urandom(_SALT_BYTES).hex()
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000
    )
    return salt, dk.hex()


def _verify_password(password, stored_hash, stored_salt):
    """Return True if *password* matches the stored PBKDF2 hash."""
    _, dk = _hash_password(password, stored_salt)
    return hmac.compare_digest(dk, stored_hash)


def _is_valid_username(username):
    """
    Return True if *username* contains only safe characters.
    This also prevents path-traversal when the username is used in file names.
    """
    return bool(re.match(r"^[a-zA-Z0-9_\-]{1,50}$", username))


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login():
    """
    Prompt for username and password.
    Creates a new account if the username does not yet exist.
    Returns the authenticated username.
    """
    print("\n" + "=" * 50)
    print("        PYTHON QUIZ APPLICATION")
    print("=" * 50)

    users = _load_users()

    while True:
        username = input("\nUsername: ").strip()
        if not username:
            print("❌ Username cannot be empty.")
            continue

        if not _is_valid_username(username):
            print(
                "❌ Username may only contain letters, numbers, underscores, "
                "and hyphens (1–50 characters)."
            )
            continue

        password = getpass.getpass("Password: ")
        if not password:
            print("❌ Password cannot be empty.")
            continue

        if username in users:
            stored = users[username]
            stored_hash = stored.get("password", "")
            stored_salt = stored.get("salt", "")
            if stored_hash and stored_salt and _verify_password(password, stored_hash, stored_salt):
                print(f"\n✅ Login successful! Welcome back, {username}.")
                return username
            print("❌ Incorrect password. Please try again.")
        else:
            print(f"\nNo account found for '{username}'.")
            choice = input("Create a new account? (y/n): ").strip().lower()
            if choice == "y":
                confirm = getpass.getpass("Confirm password: ")
                if password == confirm:
                    salt, hashed = _hash_password(password)
                    users[username] = {"password": hashed, "salt": salt}
                    _save_users(users)
                    print(f"✅ Account created! Welcome, {username}.")
                    return username
                print("❌ Passwords do not match. Please try again.")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def _show_dashboard(username):
    """Display the main menu and route to quiz or stats modules."""
    from quiz import run_quiz
    from stats import view_statistics

    def _on_exit():
        print(f"\n👋 Goodbye, {username}! You have been logged out.")

    atexit.register(_on_exit)

    try:
        while True:
            print("\n" + "=" * 50)
            print(f"   Welcome back, {username}!")
            print("=" * 50)
            print("  1. Start New Quiz")
            print("  2. View Statistics")
            print("  3. Logout")
            print("=" * 50)

            choice = input("\nSelect an option (1-3): ").strip()

            if choice == "1":
                run_quiz(username)
            elif choice == "2":
                view_statistics(username)
            elif choice == "3":
                atexit.unregister(_on_exit)
                print(f"\n👋 Goodbye, {username}!")
                break
            else:
                print("❌ Invalid option. Please enter 1, 2, or 3.")
    finally:
        # Ensure _on_exit is not called again via atexit if we exit cleanly
        atexit.unregister(_on_exit)


# ---------------------------------------------------------------------------
# Signal handlers for auto-logout on terminal close
# ---------------------------------------------------------------------------

def _setup_signal_handlers():
    """
    Register handlers for SIGTERM and SIGHUP so that closing the terminal
    (or sending a termination signal) cleanly logs the user out.
    """
    def _handle_signal(sig, frame):  # noqa: ARG001
        print("\n⚠️  Session terminated. You have been automatically logged out.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        # SIGHUP is sent when a terminal tab/window is closed (Unix only)
        signal.signal(signal.SIGHUP, _handle_signal)
    except AttributeError:
        pass  # SIGHUP is not available on Windows


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    _setup_signal_handlers()
    username = login()
    _show_dashboard(username)


if __name__ == "__main__":
    main()
