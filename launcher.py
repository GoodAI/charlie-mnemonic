import os
from typing import List, Type

from fastapi import FastAPI, APIRouter
from starlette.middleware.base import BaseHTTPMiddleware

from config import origins


def default_middleware() -> List[Type[BaseHTTPMiddleware]]:
    from configuration_page.middleware import LoginAdminMiddleware
    from configuration_page.redirect_middleware import RedirectToConfigurationMiddleware
    from configuration_page.middleware import LoginRequiredCheckMiddleware

    result = [RedirectToConfigurationMiddleware, LoginRequiredCheckMiddleware]

    from configuration_page.settings_util import is_single_user

    if is_single_user():
        result.append(LoginAdminMiddleware)
    return result


def default_routers() -> List[APIRouter]:
    from configuration_page.routes import router as configuration_router
    from routes import router
    from user_management.routes import router as user_management_router

    return [user_management_router, configuration_router, router]


def create_app(
    middlewares: List[BaseHTTPMiddleware] = None, routers: List[APIRouter] = None
) -> FastAPI:
    from configuration_page import reload_configuration

    reload_configuration()
    from fastapi.middleware.cors import CORSMiddleware
    import os
    import nltk
    import logs
    import utils
    from database import Database

    nltk.download("punkt")

    version = utils.SettingsManager.get_version()

    db = Database()
    db.setup_database()

    # Defining the FastAPI app and metadata
    app = FastAPI(
        title="CLANG API",
        description="""### API specifications\n
    Welcome to the `CLANG` API documentation,\n
    WIP.
    """,
        version=version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("shutdown")
    def shutdown_event():
        logs.Log("main", "main.log").get_logger().debug("Shutting down server")

    for router in routers or default_routers():
        app.include_router(router)

    for middleware_class in middlewares or default_middleware():
        app.add_middleware(middleware_class)

    return app


def create_parser():
    import argparse

    arg_parser = argparse.ArgumentParser(description="Run web server")
    arg_parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to run the app on (default: %(default)s)",
    )
    arg_parser.add_argument(
        "--port",
        type=int,
        default=os.getenv("PORT", 8002),
        help="Port to run the app on (default: %(default)s)",
    )
    return arg_parser


if __name__ == "__main__":
    import uvicorn

    parser = create_parser()
    args = parser.parse_args()
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=False, workers=1)
