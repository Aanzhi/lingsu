"""断言默认模板蓝图的结构：三套各 22 阶段、5 大阶段前缀、交付物与指引完整。"""
from django.test import TestCase

from apps.core.services import DEFAULT_TEMPLATE_BLUEPRINTS

EXPECTED_PHASES = {
    "research": ["立项与开题", "方案与设计", "调研与实验", "成果整理", "答辩与展示"],
    "engineering": ["立项与开题", "方案与设计", "制作与测试", "成果整理", "答辩与展示"],
    "invention": ["立项与开题", "方案与设计", "制作与测试", "成果整理", "答辩与展示"],
}


class TemplateBlueprintTestCase(TestCase):
    def test_each_category_has_22_stages(self):
        for category, (name, stages) in DEFAULT_TEMPLATE_BLUEPRINTS.items():
            self.assertEqual(len(stages), 22, f"{category} 应有 22 个阶段，实际 {len(stages)}")

    def test_required_fields_present(self):
        for category, (name, stages) in DEFAULT_TEMPLATE_BLUEPRINTS.items():
            for i, (stage_name, task_name, desc, material, report_section, guidance) in enumerate(stages, 1):
                self.assertTrue(stage_name.strip(), f"{category} 第 {i} 步 stage_name 为空")
                self.assertTrue(task_name.strip(), f"{category} 第 {i} 步 task_name 为空")
                self.assertTrue(material.strip(), f"{category} 第 {i} 步 material_title 为空")
                self.assertTrue(report_section.strip(), f"{category} 第 {i} 步 report_section 为空")
                self.assertTrue(guidance.strip(), f"{category} 第 {i} 步 guidance 为空")

    def test_five_phase_prefixes(self):
        for category, (name, stages) in DEFAULT_TEMPLATE_BLUEPRINTS.items():
            prefixes: list[str] = []
            for (stage_name, *rest) in stages:
                prefix = stage_name.split("·")[0].strip()
                if prefix not in prefixes:
                    prefixes.append(prefix)
            self.assertEqual(prefixes, EXPECTED_PHASES[category], f"{category} 阶段前缀分布不符")

    def test_report_sections_unique(self):
        for category, (name, stages) in DEFAULT_TEMPLATE_BLUEPRINTS.items():
            sections = [stage[4] for stage in stages]
            self.assertEqual(len(sections), len(set(sections)), f"{category} 存在重复 report_section")

    def test_material_titles_unique(self):
        for category, (name, stages) in DEFAULT_TEMPLATE_BLUEPRINTS.items():
            titles = [stage[3] for stage in stages]
            self.assertEqual(len(titles), len(set(titles)), f"{category} 存在重复 material_title")
