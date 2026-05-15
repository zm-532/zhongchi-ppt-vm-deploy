"""Asset scanning and matching tools for Zhongchi intelligent PPT demo."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .catalog import AssetCatalog, scan_asset_directory


def main() -> None:
    parser = argparse.ArgumentParser(description="中驰智能PPT Demo 素材工具。")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # scan 命令：扫描目录生成 catalog JSON
    scan_parser = subparsers.add_parser("scan", help="扫描素材目录生成 JSON catalog")
    scan_parser.add_argument("source", help="素材根目录")
    scan_parser.add_argument("--output", default="assets_catalog.json", help="输出 JSON 路径")

    # build-vector 命令：从 catalog 或目录构建向量库
    build_parser = subparsers.add_parser("build-vector", help="从 catalog JSON 或目录构建向量库")
    build_parser.add_argument("source", help="素材 catalog JSON 路径或素材根目录")
    build_parser.add_argument("--module-id", dest="module_id", help="仅构建指定模块（如 M1、M2、M5、M6）")
    build_parser.add_argument("--batch-size", dest="batch_size", type=int, default=32, help="Embedding 批大小")

    args = parser.parse_args()

    if args.command == "scan":
        scan_handler(args)
    elif args.command == "build-vector":
        build_vector_handler(args)
    else:
        parser.print_help()
        sys.exit(1)


def scan_handler(args: argparse.Namespace) -> None:
    """Handle the scan command."""
    assets = scan_asset_directory(Path(args.source))
    output_path = AssetCatalog(assets).save_json(args.output)
    print(f"scanned={len(assets)} output={output_path}")


def build_vector_handler(args: argparse.Namespace) -> None:
    """Handle the build-vector command."""
    source_path = Path(args.source)

    # Check if source is a catalog JSON or a directory
    if source_path.suffix == ".json" and source_path.exists():
        # Load from catalog JSON
        with open(source_path, encoding="utf-8") as f:
            catalog_data = json.load(f)
        assets = [dict(a) for a in catalog_data]
        print(f"loaded {len(assets)} assets from catalog: {source_path}")
    elif source_path.is_dir():
        # Scan directory to build catalog
        assets = scan_asset_directory(source_path)
        assets = [asdict(a) for a in assets]
        print(f"scanned {len(assets)} assets from directory: {source_path}")
    else:
        print(f"Error: source must be a catalog JSON file or a directory: {source_path}")
        sys.exit(1)

    # Filter by module_id if specified
    if args.module_id:
        assets = [a for a in assets if a.get("module_id") == args.module_id]
        print(f"filtered to {len(assets)} assets for module {args.module_id}")

    if not assets:
        print("No assets to index.")
        sys.exit(0)

    # Import embedding and vector store
    # asset_tools/cli.py -> asset_tools/ -> code/ -> backend/src
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))
    try:
        from app.chunking import chunk_text
        from app.embedding import create_embedding_provider
        from app.vector_service import ChunkMetadata, get_vector_store
    except ImportError as exc:
        print(f"Error: Could not import backend modules: {exc}")
        print("Make sure the backend dependencies are installed: uv pip install -e ../backend")
        sys.exit(1)

    vector_store = get_vector_store()
    embedding_provider = create_embedding_provider()

    if not vector_store.is_available():
        print("Error: ZHONGCHI_VECTOR_DSN is not configured. Vector store is not available.")
        print("Set the environment variable: export ZHONGCHI_VECTOR_DSN='postgresql://...'")
        sys.exit(1)

    indexed_chunks = 0
    indexed_assets = 0
    skipped = 0

    for asset in assets:
        asset_id = asset.get("asset_id", 0)
        module_id = asset.get("module_id", "")
        title = asset.get("title", "")
        tags = asset.get("tags", [])
        source_path_str = asset.get("source_path", "")
        text = asset.get("text", "")

        # Try to read text from source_path if text is empty
        if not text and source_path_str:
            try:
                text = Path(source_path_str).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass

        if not text or not text.strip():
            print(f"  Skipping asset {asset_id} ({title}): empty text")
            skipped += 1
            continue

        # Chunk the text
        chunks = chunk_text(text)
        if not chunks:
            print(f"  Skipping asset {asset_id} ({title}): no chunks")
            skipped += 1
            continue

        # Generate embeddings
        try:
            embeddings = embedding_provider.embed(chunks)
        except Exception as exc:
            print(f"  Error embedding asset {asset_id} ({title}): {exc}")
            skipped += 1
            continue

        # Build metadata for each chunk
        metadata: list[ChunkMetadata] = []
        for idx, chunk in enumerate(chunks):
            meta = ChunkMetadata(
                filename=title or str(asset_id),
                source_path=source_path_str,
                document_role="asset_material",
                assigned_modules=[module_id] if module_id else [],
                chunk_index=idx,
                project_id=0,  # Assets don't belong to a project
                file_id=0,
                doc_type="asset",
                asset_id=asset_id,
                module_id=module_id,
                title=title,
                tags=tags,
            )
            metadata.append(meta)

        # Upsert to vector store
        try:
            inserted = vector_store.upsert(chunks, embeddings, metadata)
            indexed_chunks += inserted
            indexed_assets += 1
            print(f"  Indexed asset {asset_id} ({title}): {inserted} chunks")
        except Exception as exc:
            print(f"  Error upserting asset {asset_id} ({title}): {exc}")
            skipped += 1
            continue

    print(f"\nBuild complete: {indexed_assets} assets, {indexed_chunks} chunks indexed, {skipped} skipped")


if __name__ == "__main__":
    main()