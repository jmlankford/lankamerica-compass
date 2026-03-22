"""
main.py — Entry point for LankAmerica Compass Personal Financial Planner
"""
import sys
import os
from pathlib import Path

# Ensure the project root is on sys.path when running as script
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from src.ui.splash import SplashScreen
from src.ui.login_window import LoginWindow
from src.ui.main_window import MainWindow
from src.ui.styles import STYLESHEET
from src.database import Database
from src.utils import load_config, get_db_default_path


def main():
    # High-DPI support
    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')

    app = QApplication(sys.argv)
    app.setApplicationName("LankAmerica Compass")
    app.setApplicationDisplayName("LankAmerica Compass")
    app.setOrganizationName("LankAmerica")
    app.setOrganizationDomain("lankamerica.com")
    app.setStyleSheet(STYLESHEET)

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Show splash screen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Prepare state
    login_window = None
    main_window = None

    def show_login():
        nonlocal login_window
        if main_window:
            main_window.hide()
        login_window = LoginWindow()
        login_window.login_success.connect(on_login_success)
        login_window.show()

    def on_login_success(user_dict: dict, db_path: str):
        nonlocal main_window, login_window
        try:
            db = Database(db_path)
            # Re-fetch full user row (login window may have a partial dict)
            full_user = db.get_user_by_id(user_dict['id'])
            if full_user:
                user_dict = dict(full_user)
        except Exception as e:
            if login_window:
                # Can't open DB
                login_window._show_login_error(f"Could not open database: {e}")
            return

        if login_window:
            login_window.hide()

        main_window = MainWindow(db, user_dict)
        main_window.logout_requested.connect(lambda: (main_window.close(), show_login()))
        main_window.show()

    # Close splash after 2.5 seconds then show login
    splash.finish_with_delay(show_login, 2500)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
