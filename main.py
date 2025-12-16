"""Synapse - Single-user Windows desktop LLM chat client.

Entry point for the application.
"""

import sys
import asyncio

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from synapse.ui.main_window import MainWindow


def main() -> int:
    """Run the Synapse application.

    Returns:
        Exit code
    """
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Synapse")
    app.setApplicationVersion("0.1.0")

    # Set up asyncio event loop with Qt integration
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run event loop
    with loop:
        return loop.run_forever()


if __name__ == "__main__":
    sys.exit(main())
