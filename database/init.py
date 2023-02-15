from database import models


def run():
    models.Base.metadata.create_all(bind=models.engine)


# Run this with: python3 -m database.init
if __name__ == "__main__":
    run()
