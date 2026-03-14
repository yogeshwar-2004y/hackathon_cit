from fastapi import FastAPI
from core.modules import init_routers, make_middleware
from core.database import engine, Base




def create_app() -> FastAPI:
    app_ = FastAPI(
        title="FastAP",
        version="1.0.0",
        middleware=make_middleware(),
    )

    # create tables
    Base.metadata.create_all(bind=engine)

    init_routers(app_=app_)
    return app_


app = create_app()