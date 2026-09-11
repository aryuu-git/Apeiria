"""Start the Apeiria loopback management WebUI."""

import argparse
from pathlib import Path

from apeiria_webui import ApeiriaWebUIServer, WebUIContext

DEFAULT_DB = Path("runtime/AstrBot/data/plugin_data/astrbot_plugin_apeiria/state.db")
DEFAULT_CONFIG = Path("runtime/AstrBot/data/config/astrbot_plugin_apeiria_config.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6186)
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:6185")
    args = parser.parse_args()

    context = WebUIContext(
        db_path=args.db,
        config_path=args.config,
        dashboard_url=args.dashboard_url,
    )
    server = ApeiriaWebUIServer(context, args.host, args.port)
    print(f"Apeiria WebUI ready at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
