import os
import uvicorn
from gateway.app import app

PORT = int(os.environ.get("GATEWAY_PORT", "8080"))


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
