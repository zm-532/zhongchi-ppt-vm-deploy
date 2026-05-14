from __future__ import annotations

import argparse
from pathlib import Path

from .catalog import AssetCatalog, scan_asset_directory


def main() -> None:
    parser = argparse.ArgumentParser(description="扫描中驰智能PPT Demo 素材目录并生成资产 JSON。")
    parser.add_argument("source", help="素材根目录，例如 D:\\中驰股份\\SR智能PPT拆分")
    parser.add_argument("--output", default="assets_catalog.json", help="输出 JSON 路径")
    args = parser.parse_args()

    assets = scan_asset_directory(Path(args.source))
    output_path = AssetCatalog(assets).save_json(args.output)
    print(f"scanned={len(assets)} output={output_path}")


if __name__ == "__main__":
    main()

