from __future__ import annotations

from flasgo import Flasgo

custom_app = Flasgo(settings={"CSRF_ENABLED": False})
