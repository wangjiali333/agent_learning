from myAgents.core.message import Message

if __name__ == "__main__":
    msg = Message(content="你好", role="user")
    print(msg)
    print(msg.to_dict())