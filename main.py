import asyncio
from bot_config import main
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    asyncio.run(main())
