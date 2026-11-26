import logging
from threading import Event

from app.config import settings

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Automation service is idle; no jobs are configured yet.")
    Event().wait()


if __name__ == "__main__":
    main()
