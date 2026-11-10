from __future__ import annotations

import sys

from sistema.ui import SistemaApp


def main() -> int:
    app = SistemaApp()
    if "--smoke-test" in sys.argv:
        app.after(1400, app.destroy)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
