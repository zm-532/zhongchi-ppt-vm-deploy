import tempfile
import unittest
from pathlib import Path

from asset_tools.catalog import AssetCatalog, classify_module, scan_asset_directory
from asset_tools.matcher import KeywordAssetMatcher
from asset_tools.vector_store import PgVectorConfig, PgVectorStore


class AssetToolsTest(unittest.TestCase):
    def test_classify_module_uses_m1_m2_m5_m6_keywords_only(self):
        samples = {
            "行业政策 技术标准 产品趋势": "M1",
            "项目概况 现场挑战 客户痛点 工况": "M2",
            "项目基本情况 概况": "M2",
            "同类型案例 历史项目 解决成效": "M5",
            "企业介绍 CNAS 专利 荣誉 资质": "M6",
            "生产质量保障能力 原材料保障情况 产品检测计划": "M6",
            "定制化设计 工程量 工期": None,
            "技术深化部署 项目图纸深化建议 声屏障实施方案": None,
        }

        for text, expected in samples.items():
            with self.subTest(text=text):
                self.assertEqual(classify_module(text), expected)

    def test_scan_asset_directory_outputs_module_filtered_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "M1行业标准.txt").write_text("声屏障行业政策和技术标准", encoding="utf-8")
            (root / "现场挑战.txt").write_text("项目概况包含现场挑战和客户痛点", encoding="utf-8")
            (root / "企业荣誉.txt").write_text("企业介绍 CNAS 专利 荣誉 资质", encoding="utf-8")
            (root / "后续动态.txt").write_text("M3 定制化设计方案 M4 工程量测算", encoding="utf-8")

            assets = scan_asset_directory(root)

            self.assertEqual([asset.module_id for asset in assets], ["M1", "M2", "M6"])
            self.assertTrue(all(asset.module_id in {"M1", "M2", "M5", "M6"} for asset in assets))
            self.assertTrue(all(asset.source_path for asset in assets))
            self.assertTrue(all(asset.tags for asset in assets))

    def test_keyword_matcher_filters_by_module_before_scoring(self):
        catalog = AssetCatalog(
            assets=[
                {
                    "asset_id": 1,
                    "module_id": "M1",
                    "title": "行业政策素材",
                    "text": "行业政策 技术标准",
                    "tags": ["行业政策", "技术标准"],
                    "source_path": "m1.txt",
                },
                {
                    "asset_id": 2,
                    "module_id": "M5",
                    "title": "历史案例素材",
                    "text": "历史项目 同类型案例 解决成效",
                    "tags": ["同类型案例", "解决成效"],
                    "source_path": "m5.txt",
                },
            ]
        )
        matcher = KeywordAssetMatcher(catalog)

        results = matcher.match("M5", query="行业政策 同类型案例", top_k=3)

        self.assertEqual([result.asset_id for result in results], [2])
        self.assertGreater(results[0].score, 0)

    def test_pgvector_store_is_explicitly_placeholder_without_connection(self):
        config = PgVectorConfig(enabled=False)
        store = PgVectorStore(config)

        self.assertFalse(store.is_available())
        with self.assertRaises(NotImplementedError) as context:
            store.search(module_id="M1", embedding=[0.1, 0.2], top_k=3)

        self.assertIn("关键词/标签 fallback", str(context.exception))


if __name__ == "__main__":
    unittest.main()
