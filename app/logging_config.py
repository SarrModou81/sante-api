import logging


def configure_logging(app):
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(app.config.get("LOG_LEVEL", "INFO"))
    app.logger.propagate = False