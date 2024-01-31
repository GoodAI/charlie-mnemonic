import argparse
import os

import uvicorn

from configuration_page.middleware import LoginRequiredCheckMiddleware


def create_app():
    from configuration_page import reload_configuration

    reload_configuration()
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import os
    from routes import router
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

    origins = os.environ["ORIGINS"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("shutdown")
    def shutdown_event():
        logs.Log("main", "main.log").get_logger().debug("Shutting down server")

    app.include_router(router)
    from configuration_page.redirect_middleware import RedirectToConfigurationMiddleware

    app.add_middleware(RedirectToConfigurationMiddleware)
    app.add_middleware(LoginRequiredCheckMiddleware)

    from configuration_page.settings_util import is_single_user

    if is_single_user():
        from configuration_page.middleware import LoginAdminMiddleware

        app.add_middleware(LoginAdminMiddleware)
    return app


def create_parser() -> argparse.ArgumentParser:
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
    parser = create_parser()
    args = parser.parse_args()
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=False, workers=1)
