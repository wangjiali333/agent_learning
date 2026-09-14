from myAgents.core.config import Config

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    config = Config.from_env()
    print(config)
    print(config.to_dict())