import os

import openai
import uvicorn


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

    from configuration_page.settings_util import is_single_user

    if is_single_user():
        from configuration_page.user_hack_middleware import LoginAdminMiddleware

        app.add_middleware(LoginAdminMiddleware)
    return app


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host=host, port=port, reload=False, workers=1)
