from __future__ import annotations

try:
    import modal
except ImportError as exc:  # pragma: no cover - optional dependency path
    raise RuntimeError("Install Modal first: pip install modal") from exc


image = modal.Image.debian_slim().pip_install_from_requirements("requirements.txt")
modal_app = modal.App("tom-coordination-fastapi")


@modal_app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    from webapp.api.main import app

    return app
