from fastapi import FastAPI


def create_app():
    app_ = FastAPI(title="My FastAPI App")
    return app_


app = create_app()