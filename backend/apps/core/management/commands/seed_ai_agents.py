"""Seed K12-oriented AI agent templates (idempotent).

Run:
    python manage.py seed_ai_agents            # create missing global templates
    python manage.py seed_ai_agents --reset    # overwrite fields of existing ones
"""
from django.core.management.base import BaseCommand

from apps.core.models import AgentTemplate

GUARDRAIL = (
    "你是青少年科创项目教练。只提供可编辑建议，不虚构任何数据、参考文献或实验结果；"
    "不替用户提交、审核或发布；明确指出需要用户自行核实的事实与依据。"
)


def _student(direction):
    return f"{GUARDRAIL} 专注帮助学生{direction}"


def _teacher(direction):
    return f"{GUARDRAIL} 专注帮助教师{direction}"


LEGACY_AGENTS = [
    # ---------------- 学生侧（9） ----------------
    {
        "key": "opening-report",
        "name": "开题报告助手",
        "role": "student",
        "category": "开题",
        "description": "梳理论证链条与开题结构。",
        "system_instruction": _student("梳理论证链条与撰写开题报告。"),
        "prompt_template": (
            "请结合以下信息，帮助学生梳理开题报告的结构与要点：\n"
            "项目题目：{project_title}\n研究问题：{research_question}\n初步设想：{initial_idea}\n"
            "请输出：研究背景、研究目标、核心研究问题、初步方法与技术路线、预期成果与风险。"
        ),
        "input_schema": [
            {"key": "project_title", "label": "项目题目", "placeholder": "例如：校园雨水回收系统", "required": True, "type": "text"},
            {"key": "research_question", "label": "研究问题", "placeholder": "你想解决/弄清楚什么", "required": True, "type": "text"},
            {"key": "initial_idea", "label": "初步设想", "placeholder": "你已有的思路和方案", "required": True, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "experiment-plan",
        "name": "实验方案设计",
        "role": "student",
        "category": "实验",
        "description": "把研究问题转成可执行的实验/调查方案。",
        "system_instruction": _student("把研究问题转化为可执行的实验或调查方案。"),
        "prompt_template": (
            "请为学生设计一份可执行的实验或调查方案：\n"
            "研究问题：{research_question}\n已有条件：{resources}\n需要控制的因素：{variables}\n"
            "请输出：变量定义（自变量/因变量/控制变量）、步骤、样本与重复、数据记录方式、安全注意事项。"
        ),
        "input_schema": [
            {"key": "research_question", "label": "研究问题", "placeholder": "要回答的科学问题", "required": True, "type": "text"},
            {"key": "resources", "label": "已有条件", "placeholder": "设备、材料、场地等", "required": False, "type": "textarea"},
            {"key": "variables", "label": "需要控制的因素", "placeholder": "可能干扰结果的变量", "required": False, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": True, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "experiment-record",
        "name": "实验记录整理",
        "role": "student",
        "category": "实验",
        "description": "把零散观察整理成规范实验记录。",
        "system_instruction": _student("把零散观察整理成规范的实验记录。"),
        "prompt_template": (
            "学生提供了以下原始观察/记录片段，请帮忙整理成规范的实验记录表与要点：\n"
            "原始记录：{raw_notes}\n记录日期：{record_date}\n"
            "请输出：结构化实验记录（时间、操作、现象、数据）、异常与待核实项。"
        ),
        "input_schema": [
            {"key": "raw_notes", "label": "原始记录", "placeholder": "粘贴你的观察笔记", "required": True, "type": "textarea"},
            {"key": "record_date", "label": "记录日期", "placeholder": "如 2026-08-18", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "data-interpret",
        "name": "数据解释",
        "role": "student",
        "category": "写作",
        "description": "解读数据趋势，提醒需真实统计验证。",
        "system_instruction": _student("解读数据趋势并提示需真实统计验证之处。"),
        "prompt_template": (
            "请解释以下数据，并提醒学生哪些结论需要真实统计验证：\n"
            "数据描述：{data_description}\n图表意图：{chart_intent}\n"
            "请输出：趋势描述、可能的解释、不确定性与需核实的统计方法。"
        ),
        "input_schema": [
            {"key": "data_description", "label": "数据描述", "placeholder": "数值、表格或观察结果", "required": True, "type": "textarea"},
            {"key": "chart_intent", "label": "图表意图", "placeholder": "你想用图表达什么", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": True, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "research-report",
        "name": "研究报告起草",
        "role": "student",
        "category": "写作",
        "description": "基于项目资料起草报告大纲与初稿要点。",
        "system_instruction": _student("基于项目资料起草研究报告。"),
        "prompt_template": (
            "请基于项目资料起草研究报告/论文大纲与初稿要点，建议结构：引言、理论基础与文献综述、研究方法、研究结果、讨论、结论、参考文献"
            "（实证/案例可相应扩展样本与分析、案例描述）。\n"
            "写作重点：{focus}\n目标读者：{audience}\n"
            "请输出：报告结构、各节要点、需要补充的真实证据清单（标注“待补充”）。"
        ),
        "input_schema": [
            {"key": "focus", "label": "写作重点", "placeholder": "本次想突出的内容", "required": True, "type": "textarea"},
            {"key": "audience", "label": "目标读者", "placeholder": "选择读者", "required": True, "type": "select", "options": ["同学", "教师", "竞赛评委"]},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": True, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "defense-prep",
        "name": "答辩问答准备",
        "role": "student",
        "category": "答辩",
        "description": "生成答辩高频提问与应答思路。",
        "system_instruction": _student("准备答辩提问与应答思路。"),
        "prompt_template": (
            "请针对以下项目生成答辩可能提问与学生应答思路：\n"
            "项目亮点：{highlights}\n薄弱环节：{weakness}\n"
            "请输出：10 个高频提问、每题应答要点、以及需要学生用真实数据支撑的地方。"
        ),
        "input_schema": [
            {"key": "highlights", "label": "项目亮点", "placeholder": "你最自豪的成果", "required": True, "type": "textarea"},
            {"key": "weakness", "label": "薄弱环节", "placeholder": "可能被质疑的地方", "required": False, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": True, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "literature-questions",
        "name": "文献查阅问题清单",
        "role": "student",
        "category": "写作",
        "description": "生成检索问题清单与关键词组合（不虚构文献）。",
        "system_instruction": _student("高效检索文献，不虚构具体文献。"),
        "prompt_template": (
            "请生成文献查阅与精读辅助，不虚构具体文献：\n"
            "主题：{topic}\n已知关键词：{keywords}\n"
            "请输出两部分：\n"
            "一、检索清单：检索问题、推荐关键词组合、应核实的信息类型。\n"
            "二、带着问题读文献：围绕该主题，列出通用阅读问题（主要研究问题是什么、研究方法有哪些、创新点与贡献、局限性与未来方向、论文结构如何组织、关键数据图表说明什么），帮助学生高效精读与做笔记。"
        ),
        "input_schema": [
            {"key": "topic", "label": "主题", "placeholder": "研究主题", "required": True, "type": "text"},
            {"key": "keywords", "label": "已知关键词", "placeholder": "已有的中英文关键词", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "polish-expand",
        "name": "文本润色扩写",
        "role": "student",
        "category": "写作",
        "description": "润色扩写，不添加未经证实的事实。",
        "system_instruction": _student("润色扩写文本，不添加未经证实的事实。"),
        "prompt_template": (
            "请作为中文学术论文写作改进助理处理下列文本，保持原意与事实，不添加未经证实的内容：\n"
            "原文：{draft}\n风格：{tone}\n"
            "若以润色为主：先用表格对比原句/修改版/原因（粗体标注改动），再给完整文本；"
            "若以扩写为主：输出衔接自然、论证更充分的文本与改动说明。"
        ),
        "input_schema": [
            {"key": "draft", "label": "原文", "placeholder": "粘贴需要润色的文字", "required": True, "type": "textarea"},
            {"key": "tone", "label": "风格", "placeholder": "选择风格", "required": True, "type": "select", "options": ["学术", "通俗", "简洁"]},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "format-proof",
        "name": "格式与校对",
        "role": "student",
        "category": "写作",
        "description": "检查错别字、引用/单位格式与结构一致性。",
        "system_instruction": _student("检查文本格式、错别字与一致性。"),
        "prompt_template": (
            "请对以下文本做学术校对与格式检查（参考 GB/T 7714 等规范）：\n"
            "文本：{text}\n格式要求：{format}\n"
            "请输出按严重程度排序的问题清单：①拼写/语法/标点；②格式与样式合规；"
            "③引用与参考文献准确性（文中引用与文末列表交叉核对）；④表格、图形、图表标签与对齐；"
            "⑤整体清晰度与可读性，并给出修正建议。"
        ),
        "input_schema": [
            {"key": "text", "label": "文本", "placeholder": "粘贴需要校对的文字", "required": True, "type": "textarea"},
            {"key": "format", "label": "格式要求", "placeholder": "如 GB/T 7714、学校模板", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    # ---------------- 论文写作（基于用户提供的提示词大全） ----------------
    {
        "key": "topic-selection-paper",
        "name": "论文选题与标题",
        "role": "student",
        "category": "写作",
        "description": "结合学科背景生成可参考的论文选题与标题。",
        "system_instruction": _student("确定论文选题与标题，给出可参考方向与命名，不虚构文献。"),
        "prompt_template": (
            "#上下文#\n"
            "我在撰写学术论文，学科领域：{field}；已有研究基础或经验：{foundation}；基础思路：{idea}。\n"
            "#目标#\n结合上下文，提供 5 个可供参考和使用的论文选题/标题，并简述每个的切入角度。\n"
            "#风格#\n仿效优秀期刊学术论文。\n#语气#\n严谨、正式、符合学术规范。\n"
            "#受众#\n论文评审专家，请确保准确性。\n"
            "#回复#\n给出表格：第一列论文名称，第二列研究内容，第三列关键词，第四列研究方法，第五列推荐理由（含推荐度）。"
        ),
        "input_schema": [
            {"key": "field", "label": "学科领域", "placeholder": "如 教育学、生物学", "required": True, "type": "text"},
            {"key": "foundation", "label": "已有基础", "placeholder": "已有的研究基础或经验", "required": False, "type": "textarea"},
            {"key": "idea", "label": "基础思路", "placeholder": "你初步想研究的方向", "required": True, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "paper-framework",
        "name": "论文框架生成",
        "role": "student",
        "category": "写作",
        "description": "据题目与研究思路生成论文结构框架与各节写法。",
        "system_instruction": _student("构建论文结构框架并说明各部分写法。"),
        "prompt_template": (
            "#上下文#\n论文题目：{title}；研究思路：{research_idea}。\n"
            "#目标#\n提供一个可供参考的论文框架，并简述每一部分要写的内容（建议按 引言/理论基础与文献综述/研究方法/研究结果/讨论/结论/参考文献 组织；实证研究可补充样本与分析，案例研究可补充案例描述）。\n"
            "#风格#\n仿效优秀期刊学术论文。\n#语气#\n严谨、正式、符合学术规范。\n#受众#\n论文评审专家。\n"
            "#回复#\n直接给出研究框架及每部分要点。"
        ),
        "input_schema": [
            {"key": "title", "label": "论文题目", "placeholder": "你的论文题目", "required": True, "type": "text"},
            {"key": "research_idea", "label": "研究思路", "placeholder": "你想研究/论证的核心", "required": True, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "literature-review-paper",
        "name": "文献综述起草",
        "role": "student",
        "category": "写作",
        "description": "起草文献综述提纲与检索策略（不虚构文献）。",
        "system_instruction": _student("起草文献综述，梳理理论、趋势与空白，不虚构文献。"),
        "prompt_template": (
            "请基于真实文献起草或梳理论文综述，不编造任何具体文献或数据。\n"
            "研究领域：{research_field}；时间范围：{time_frame}；聚焦主题：{focus_topic}。\n"
            "请输出：关键文献与理论概述、主要发现与方法论、研究空白与待探索方向，以及需要你自行检索核实的文献清单（明确标注“待检索”）。"
        ),
        "input_schema": [
            {"key": "research_field", "label": "研究领域", "placeholder": "如 计算思维培养", "required": True, "type": "text"},
            {"key": "time_frame", "label": "时间范围", "placeholder": "如 近十年", "required": False, "type": "text"},
            {"key": "focus_topic", "label": "聚焦主题", "placeholder": "你想重点综述的子方向", "required": True, "type": "text"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "research-design-paper",
        "name": "研究设计建议",
        "role": "student",
        "category": "写作",
        "description": "把研究问题转成可执行的论文研究方法。",
        "system_instruction": _student("把研究问题转化为可执行的论文研究方法设计。"),
        "prompt_template": (
            "请为学生设计论文研究方法，明确可执行性。\n"
            "研究问题：{research_question}；倾向方法：{method_hint}（定量/定性/混合）。\n"
            "请输出：研究设计概述（方法类型、数据收集方法、样本量与抽样策略）、变量定义（自变量/因变量/控制变量）、减少偏倚与确保有效性的措施、伦理考虑，以及需要真实实施的部分。"
        ),
        "input_schema": [
            {"key": "research_question", "label": "研究问题", "placeholder": "要回答的科学问题", "required": True, "type": "text"},
            {"key": "method_hint", "label": "方法倾向", "placeholder": "定量/定性/混合，或留空", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": True, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "data-analysis-paper",
        "name": "数据分析解读",
        "role": "student",
        "category": "写作",
        "description": "解读数据趋势并标注需真实统计验证之处。",
        "system_instruction": _student("解读数据趋势与统计结果，提醒需真实统计验证。"),
        "prompt_template": (
            "请结合上下文给出结果分析，明确指出哪些结论需要真实统计验证。\n"
            "数据/实验结果描述：{data_context}；分析目标：{analysis_goal}。\n"
            "请输出：趋势与结果描述、可能的解释、显著性/不确定性说明、需补充的统计分析（如 t 检验、效应量）与待核实项。"
        ),
        "input_schema": [
            {"key": "data_context", "label": "数据/结果描述", "placeholder": "数值、表格或观察结果", "required": True, "type": "textarea"},
            {"key": "analysis_goal", "label": "分析目标", "placeholder": "你想说明什么结论", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": True, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "paper-polish",
        "name": "论文润色定稿",
        "role": "student",
        "category": "写作",
        "description": "学术化润色定稿，逐句对比并说明修改原因。",
        "system_instruction": _student("学术化润色定稿，逐句对比并说明修改原因，不添加未经证实事实。"),
        "prompt_template": (
            "#上下文#\n待润色定稿文本：{text}\n"
            "#目标#\n作为中文学术论文写作改进助理，改进文本的拼写、语法、清晰、简洁与整体可读性，分解长句、减少重复，并提供改进建议。\n"
            "#风格#\n仿效优秀期刊学术论文。\n#语气#\n严谨、正式、符合学术规范。\n#受众#\n论文评审专家。\n"
            "#回复#\n先用表格呈现原文与修改后每句对比，用粗体标注修改处，用中文解释修改原因（三列：原句、修改版、原因）；再输出修改后的完整文本。"
        ),
        "input_schema": [
            {"key": "text", "label": "待润色文本", "placeholder": "粘贴需要润色定稿的文字", "required": True, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "reference-format",
        "name": "参考文献格式整理",
        "role": "student",
        "category": "写作",
        "description": "将参考文献校正为 GB/T 7714-2015 格式。",
        "system_instruction": _student("将参考文献校正为 GB/T 7714-2015 格式，不虚构条目。"),
        "prompt_template": (
            "#上下文#\n参考文献原文：{raw_references}\n"
            "#目标#\n首先按照 GB/T 7714-2015 格式对参考文献进行校正，调整为严格符合规范的文献格式；无法确认的信息请标注“待核实”，不要虚构。\n"
            "#风格#\n学术规范。\n#语气#\n严谨。\n#受众#\n论文评审专家。\n"
            "#回复#\n请用 [1]、[2] 为序号输出规范化的参考文献列表，并简述主要修正点。"
        ),
        "input_schema": [
            {"key": "raw_references", "label": "参考文献原文", "placeholder": "粘贴待整理的参考文献", "required": True, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": False, "current_material_draft": False, "current_guidance": False},
    },
    {
        "key": "reviewer-response",
        "name": "审稿人意见回复",
        "role": "student",
        "category": "写作",
        "description": "分析审稿意见并完善作者回复与修订文本。",
        "system_instruction": _student("分析审稿意见并完善作者回复与修订文本。"),
        "prompt_template": (
            "#上下文#\n审稿人意见：{reviewer_comment}\n作者初步回复：{draft_reply}\n原始稿件对应段落：{original_text}\n"
            "#目标#\n作为学术研究专家，分析审稿人意见，判断初步回复是否合理；若不合理，完善并修正初步回复。\n"
            "#风格#\n仿效优秀期刊学术论文。\n#语气#\n严谨、正式、符合学术规范。\n#受众#\n论文评审专家/编辑。\n"
            "#回复#\n给出完善后的对审稿人的回复，以及修订后的稿件文本（标注修改处）。"
        ),
        "input_schema": [
            {"key": "reviewer_comment", "label": "审稿人意见", "placeholder": "粘贴审稿意见", "required": True, "type": "textarea"},
            {"key": "draft_reply", "label": "初步回复", "placeholder": "你写的初步回复", "required": True, "type": "textarea"},
            {"key": "original_text", "label": "原文对应段", "placeholder": "被质疑的原文段落", "required": True, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": False, "current_material_draft": False, "current_guidance": False},
    },
    {
        "key": "thesis-proposal",
        "name": "课题申报书起草",
        "role": "student",
        "category": "写作",
        "description": "撰写课题申报书核心部分（选题/背景/方案/计划）。",
        "system_instruction": _student("撰写课题申报书各部分，强调原创性与可行性。"),
        "prompt_template": (
            "#上下文#\n学科领域：{field}；已有基础：{foundation}；课题题目：{topic}；主要研究内容：{research_content}。\n"
            "#目标#\n结合上下文，帮助撰写课题申报书的核心部分（研究背景含国内外现状与评述、研究内容与方法、重点难点与创新之处、研究计划与预期成果）。\n"
            "#风格#\n仿效成功课题申报书。\n#语气#\n有说服力、严谨、正式。\n#受众#\n课题评审专家。\n"
            "#回复#\n按需输出所选部分的完整内容，强调原创性与可行性；凡需真实数据支撑处请标注“待补充”。"
        ),
        "input_schema": [
            {"key": "field", "label": "学科领域", "placeholder": "如 教育学", "required": True, "type": "text"},
            {"key": "foundation", "label": "已有基础", "placeholder": "已有的研究基础或经验", "required": False, "type": "textarea"},
            {"key": "topic", "label": "课题题目", "placeholder": "你的课题名称", "required": True, "type": "text"},
            {"key": "research_content", "label": "主要研究内容", "placeholder": "拟研究的主要内容", "required": True, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "cross-consistency",
        "name": "跨步骤一致性体检",
        "role": "student",
        "category": "写作",
        "description": "通读项目各步骤材料，评估一致性、证据覆盖度与冲突风险。",
        "system_instruction": (
            GUARDRAIL + " 专注帮助学生对整个项目做一致性体检与完成度评估：只指出前后矛盾/脱节/证据缺口的风险，"
            "不替学生编造未测数据或结论；严格输出中文 JSON 对象。"
        ),
        "prompt_template": (
            "请通读该项目全部材料，评估一致性、证据覆盖度与冲突风险。\n"
            "用户关注点：{focus}\n"
            "请只输出一个 JSON 对象，结构如下（不要输出数组以外的任何内容）：\n"
            "{\n"
            '  "coverage_score": 0-100 的整数（证据对结论的覆盖程度，越高越好）,\n'
            '  "missing_evidence": ["还缺哪些关键证据或数据的字符串数组"],\n'
            '  "conflicts": ["前后矛盾或口径不一致的字符串数组"],\n'
            '  "issues": [{"severity": "高|中|低", "title": "问题标题", "involves": ["涉及的步骤/材料"], "detail": "具体说明", "suggestion": "可执行的修改建议"}]\n'
            "}\n"
            "若未发现明显问题，issues 返回空数组、coverage_score 给一个合理高分。"
        ),
        "input_schema": [
            {"key": "focus", "label": "重点关注", "placeholder": "如 数据是否支撑结论、术语是否一致", "required": False, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": False, "consistency": True},
    },
    {
        "key": "next-step-advisor",
        "name": "下一步与落地建议",
        "role": "student",
        "category": "写作",
        "description": "基于已完成步骤与证据缺口，给出推进清单。",
        "system_instruction": (
            GUARDRAIL + " 专注帮助学生判断项目当前进度、还缺什么证据、下一步做什么；"
            "不替学生编造数据或结论，明确标注需自行实测或核实之处。"
        ),
        "prompt_template": (
            "请基于项目已完成步骤与材料，给出推进清单：\n"
            "当前进度关注：{focus}\n"
            "请只输出一个 JSON 对象（不要输出其他内容）：\n"
            "{\n"
            '  "overall_progress": "简短的整体进度判断",\n'
            '  "next_actions": [{"priority": "高|中|低", "action": "建议做的具体动作", "rationale": "为什么现在做", "related_task": "关联步骤名（可选）"}],\n'
            '  "missing_evidence": ["仍需补充的证据或数据"],\n'
            '  "risks": ["落地或方法上的风险提醒"]\n'
            "}\n"
        ),
        "input_schema": [
            {"key": "focus", "label": "当前关注", "placeholder": "如 实验数据整理、报告撰写", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": True, "approved_materials": True, "consistency": True},
    },
    # ---------------- 教师侧（6） ----------------
    {
        "key": "opening-review",
        "name": "开题审核要点",
        "role": "teacher",
        "category": "教师审核",
        "description": "以教师视角审核开题，给出可执行修改意见。",
        "system_instruction": _teacher("审核学生开题并给出可执行修改意见。"),
        "prompt_template": (
            "请基于开题材料给出审核要点：\n"
            "开题内容：{opening_text}\n项目阶段：{stage}\n"
            "请输出：科学性、可行性、安全与伦理风险、需学生补充的要点清单。"
        ),
        "input_schema": [
            {"key": "opening_text", "label": "开题内容", "placeholder": "粘贴开题报告/提纲", "required": True, "type": "textarea"},
            {"key": "stage", "label": "项目阶段", "placeholder": "如 立项、方案设计", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "material-feedback",
        "name": "材料反馈草稿",
        "role": "teacher",
        "category": "教师审核",
        "description": "为材料草稿生成结构化反馈。",
        "system_instruction": _teacher("为材料草稿生成结构化反馈。"),
        "prompt_template": (
            "请为学生的材料草稿生成反馈：\n"
            "材料内容：{material_text}\n反馈重点：{focus}\n"
            "请输出：肯定之处、需修改的问题（逐条）、可执行的修改建议。"
        ),
        "input_schema": [
            {"key": "material_text", "label": "材料内容", "placeholder": "粘贴学生材料", "required": True, "type": "textarea"},
            {"key": "focus", "label": "反馈重点", "placeholder": "最关注的方面", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "safety-risk",
        "name": "实验安全风险检查",
        "role": "teacher",
        "category": "教师审核",
        "description": "识别实验/操作中的安全与伦理风险。",
        "system_instruction": _teacher("识别实验与操作中的安全、伦理风险。"),
        "prompt_template": (
            "请检查以下实验方案的安全风险：\n"
            "方案：{plan_text}\n学段：{grade}\n"
            "请输出：风险点、等级、防护/替代方案、必须叫停的情形。"
        ),
        "input_schema": [
            {"key": "plan_text", "label": "方案", "placeholder": "粘贴实验/操作方案", "required": True, "type": "textarea"},
            {"key": "grade", "label": "学段", "placeholder": "如 初中、高中", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "version-diff",
        "name": "版本差异摘要",
        "role": "teacher",
        "category": "教师审核",
        "description": "对比两版材料，给出差异与通过建议。",
        "system_instruction": _teacher("对比两版材料并给出差异与通过建议。"),
        "prompt_template": (
            "请对比材料的两个版本，给出差异摘要：\n"
            "旧版要点：{old_text}\n新版要点：{new_text}\n"
            "请输出：主要变更、改进与遗留问题、是否建议通过。"
        ),
        "input_schema": [
            {"key": "old_text", "label": "旧版要点", "placeholder": "上一版内容", "required": True, "type": "textarea"},
            {"key": "new_text", "label": "新版要点", "placeholder": "当前版本内容", "required": True, "type": "textarea"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "public-compliance",
        "name": "公开材料合规检查",
        "role": "teacher",
        "category": "教师审核",
        "description": "检查隐私/版权/涉密等公开发布风险。",
        "system_instruction": _teacher("检查拟公开材料的隐私/版权/涉密风险。"),
        "prompt_template": (
            "请检查以下拟公开材料是否符合合规要求：\n"
            "材料：{material_text}\n公开范围：{scope}\n"
            "请输出：隐私/版权/涉密风险、必须脱敏或删除的内容、发布建议。"
        ),
        "input_schema": [
            {"key": "material_text", "label": "材料", "placeholder": "粘贴拟公开内容", "required": True, "type": "textarea"},
            {"key": "scope", "label": "公开范围", "placeholder": "如 校内、竞赛、互联网", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
    {
        "key": "peer-review",
        "name": "同伴评审草稿",
        "role": "teacher",
        "category": "教师审核",
        "description": "以同行评审视角给研究报告结构性意见。",
        "system_instruction": _teacher("以同行评审视角给研究报告结构性意见。"),
        "prompt_template": (
            "请模拟同行评审视角，给出对研究报告的结构性意见：\n"
            "报告：{report_text}\n评审标准：{criteria}\n"
            "请输出：优势、方法学问题、表述与证据链缺口、总体推荐意见。"
        ),
        "input_schema": [
            {"key": "report_text", "label": "报告", "placeholder": "粘贴研究报告", "required": True, "type": "textarea"},
            {"key": "criteria", "label": "评审标准", "placeholder": "如 科学性、创新性", "required": False, "type": "text"},
        ],
        "context_scope_default": {"project_basics": False, "approved_materials": False, "current_task": True, "current_material_draft": True, "current_guidance": True},
    },
]


def _agent(key, name, workflow, category, description, direction, prompt, inputs, stages, quick_tasks, output):
    return {
        "key": key,
        "name": name,
        "role": AgentTemplate.Role.STUDENT,
        "workflow": workflow,
        "category": category,
        "description": description,
        "system_instruction": _student(
            f"{direction}。涉及文献、数据、实验结果时只给检索、整理和核验建议，不虚构来源、数据或结论。"
        ),
        "prompt_template": prompt,
        "input_schema": inputs,
        # Context is assigned deliberately below by workflow; broad approved-material
        # injection is never the default for a single-purpose Agent.
        "context_scope_default": {},
        "applicable_stages": stages,
        "quick_tasks": quick_tasks,
        "project_types": ["research", "invention", "engineering"],
        "output_contract": output,
    }


# 科创共创中心学生端：开题/申报 5 个 + 论文写作 6 个。仅保留这 11 个全局种子，
# 以免旧的宽泛模板干扰按工作流、阶段和快捷任务的匹配。
AGENTS = [
    _agent("proposal-topic", "课题名称与摘要", "proposal_topic", "开题申报", "把兴趣转为可研究、可验证的问题。", "澄清选题边界、研究对象和核心问题", "项目主题：{topic}\n已有观察：{observations}\n请输出可比较的选题、研究问题、变量/证据线索和待核验假设。", [{"key": "topic", "label": "项目主题", "placeholder": "你想研究的主题", "required": True, "type": "text"}, {"key": "observations", "label": "已有观察", "placeholder": "现象、痛点或灵感", "required": False, "type": "textarea"}], ["立项", "选题"], ["选题建议", "问题澄清"], {"format": "sections", "sections": ["候选选题", "研究问题", "待核验假设"]}),
    _agent("proposal-background", "研究背景与意义", "proposal_background", "开题申报", "梳理论证链条与开题结构。", "梳理论证链条并撰写开题报告", "项目题目：{project_title}\n研究问题：{research_question}\n初步设想：{initial_idea}\n请输出研究背景、目标、方法、技术路线、预期成果、风险与待核验事项。", [{"key": "project_title", "label": "项目题目", "placeholder": "例如：校园雨水回收", "required": True, "type": "text"}, {"key": "research_question", "label": "研究问题", "placeholder": "要解决什么", "required": True, "type": "text"}, {"key": "initial_idea", "label": "初步设想", "placeholder": "已有思路", "required": True, "type": "textarea"}], ["立项", "开题"], ["生成开题结构", "补充研究背景"], {"format": "sections", "sections": ["背景", "目标", "方法", "风险", "核验清单"]}),
    _agent("proposal-objectives", "研究目标与内容", "proposal_objectives", "开题申报", "把研究问题转成可执行的方案。", "设计可执行的实验、调查或工程验证方案", "研究问题：{research_question}\n已有条件：{resources}\n请输出变量/指标、步骤、样本或测试条件、数据记录方式、安全事项和待核验清单。", [{"key": "research_question", "label": "研究问题", "placeholder": "要回答的问题", "required": True, "type": "text"}, {"key": "resources", "label": "已有条件", "placeholder": "设备、材料、场地", "required": False, "type": "textarea"}], ["方案设计", "研究设计"], ["设计实验", "设计调查"], {"format": "checklist", "sections": ["变量与指标", "步骤", "数据记录", "安全与核验"]}),
    _agent("proposal-plan", "实施方案与进度", "proposal_plan", "开题申报", "识别资源、伦理、安全和进度风险。", "检查方案可行性并提出可执行的风险缓解措施", "方案摘要：{plan_summary}\n限制条件：{constraints}\n请输出风险矩阵、缓解措施、资源缺口与需要教师/学生核实的事项。", [{"key": "plan_summary", "label": "方案摘要", "placeholder": "简述你的方案", "required": True, "type": "textarea"}, {"key": "constraints", "label": "限制条件", "placeholder": "时间、设备或安全限制", "required": False, "type": "textarea"}], ["开题", "方案设计"], ["检查可行性", "评估风险"], {"format": "risk_matrix", "sections": ["风险", "影响", "缓解措施", "核验项"]}),
    _agent("proposal-consistency", "申报材料一致性检查", "proposal_consistency", "开题申报", "检查研究问题、目标、方法、进度与预期成果之间是否一致。", "检查申报材料的前后逻辑和证据缺口", "申报材料：{draft}\n请输出一致项、冲突或缺失项、修正建议及所有需要学生核验的事实/数据。", [{"key": "draft", "label": "申报材料", "placeholder": "粘贴申报书片段", "required": True, "type": "textarea"}], ["开题", "申报提交"], ["一致性检查", "检查证据缺口"], {"format": "checklist", "sections": ["一致项", "问题", "修正建议", "待核验项"]}),
    _agent("paper-title-abstract", "标题与摘要助手", "paper_title_abstract", "论文写作", "形成有边界的论文标题与摘要。", "确定论文标题、摘要要点和研究切口", "论文类型：{paper_type}\n学科领域：{field}\n已有基础：{foundation}\n研究想法：{idea}\n请输出候选标题、摘要要点、关键词、方法建议与待检索事项。", [{"key": "field", "label": "学科领域", "placeholder": "如环境科学", "required": True, "type": "text"}, {"key": "foundation", "label": "已有基础", "placeholder": "已有经验", "required": False, "type": "textarea"}, {"key": "idea", "label": "研究想法", "placeholder": "初步方向", "required": True, "type": "textarea"}], ["论文选题", "摘要"], ["生成标题", "起草摘要"], {"format": "sections", "sections": ["标题", "摘要", "关键词", "待检索"]}),
    _agent("paper-framework", "论文框架助手", "paper_framework", "论文写作", "据题目生成可调整的论文结构。", "构建论文框架并说明各节证据需求", "论文题目：{title}\n研究思路：{research_idea}\n论文类型：{paper_type}\n请输出章节框架、各节要点、证据需求和待补充内容。", [{"key": "title", "label": "论文题目", "placeholder": "你的题目", "required": True, "type": "text"}, {"key": "research_idea", "label": "研究思路", "placeholder": "核心论证", "required": True, "type": "textarea"}, {"key": "paper_type", "label": "论文类型", "placeholder": "如实证、综述、案例", "required": False, "type": "text"}], ["论文写作", "框架"], ["生成论文框架", "调整章节"], {"format": "outline", "sections": ["章节", "要点", "证据需求", "待补充"]}),
    _agent("paper-expand-polish", "扩写与润色助手", "paper_expand_polish", "论文写作", "在不新增未经证实事实的前提下扩写和润色论文。", "扩写、润色并标记需要补证的内容", "论文类型：{paper_type}\n原文：{draft}\n写作目标：{goal}\n请输出修改建议、修订稿和待核验的文献/数据/事实。", [{"key": "draft", "label": "原文", "placeholder": "粘贴论文片段", "required": True, "type": "textarea"}, {"key": "goal", "label": "写作目标", "placeholder": "如扩写讨论、提升衔接", "required": False, "type": "text"}], ["论文写作", "修改"], ["扩写段落", "润色表达"], {"format": "revision", "sections": ["修改建议", "修订稿", "待核验"]}),
    _agent("paper-reference-format", "参考文献检索助手", "paper_reference_format", "论文写作", "将文献需求转为可执行、可核验的检索计划。", "只生成检索式、筛选标准和待核验候选来源；不生成任何可直接引用的文献条目、引文、DOI 或关于来源真实性的结论", "论文类型：{paper_type}\n研究主题或待核验的引用片段：{references}\n检索范围/格式要求：{style}\n仅输出三部分：（1）检索式；（2）筛选标准；（3）待核验候选来源。候选来源只能是检索方向或数据库/期刊线索，必须标注“待核验”；不得输出完整引文、DOI、页码或声称某来源真实存在。", [{"key": "references", "label": "研究主题或待核验片段", "placeholder": "粘贴主题、关键词或已有引用片段", "required": True, "type": "textarea"}, {"key": "style", "label": "检索范围或格式要求", "placeholder": "如 CNKI、Web of Science、GB/T 7714", "required": False, "type": "text"}], ["论文写作", "文献检索"], ["生成检索式", "制定筛选标准"], {"format": "reference_research_plan", "sections": ["检索式", "筛选标准", "待核验候选来源"], "prohibitions": ["不生成任何可直接引用的文献条目", "不生成 DOI、页码或虚构来源", "不声称候选来源已经真实存在或已核验"]}),
    _agent("paper-result-interpret", "结果解读助手", "paper_result_interpret", "论文写作", "把真实结果整理为谨慎的讨论。", "解读真实数据或观察并写作结果与讨论", "论文类型：{paper_type}\n真实结果/观察：{results}\n预期讨论角度：{discussion_focus}\n请区分事实、解释与推测，输出结果描述、讨论框架、局限和待核验项。", [{"key": "results", "label": "真实结果或观察", "placeholder": "粘贴已核对的数据或观察", "required": True, "type": "textarea"}, {"key": "discussion_focus", "label": "讨论角度", "placeholder": "想解释什么", "required": False, "type": "textarea"}], ["结果分析", "讨论"], ["解读结果", "起草讨论"], {"format": "sections", "sections": ["结果", "解释", "局限", "待核验"]}),
    _agent("paper-reviewer-response", "审稿意见回复助手", "paper_reviewer_response", "论文写作", "整理审稿意见并形成逐条、诚实的回复策略。", "回复审稿意见，不承诺不存在的证据或修改", "论文类型：{paper_type}\n审稿意见：{review_comments}\n当前修改：{revision_summary}\n请输出逐条回复草案、修改清单与待核验项。", [{"key": "review_comments", "label": "审稿意见", "placeholder": "粘贴审稿意见", "required": True, "type": "textarea"}, {"key": "revision_summary", "label": "当前修改", "placeholder": "已完成的修改", "required": False, "type": "textarea"}], ["修改", "投稿回复"], ["拆解审稿意见", "起草回复"], {"format": "table", "sections": ["审稿意见", "回复草案", "修改动作", "待核验"]}),
]


# Shared context is bounded to the current project in the generation task.  The
# consistency Agent is the sole template permitted to read all project materials;
# other Agents only receive the task/material explicitly associated with a run.
_SHARED_CONTEXT = {"project_basics": True, "approved_materials": False, "ai_history": True, "teacher_feedback": True}
_TASK_MATERIAL_CONTEXT = {**_SHARED_CONTEXT, "current_task": True, "current_material_draft": True, "current_guidance": True}
_CONTEXT_BY_KEY = {
    "proposal-topic": _SHARED_CONTEXT,
    "proposal-background": _TASK_MATERIAL_CONTEXT,
    "proposal-objectives": _TASK_MATERIAL_CONTEXT,
    "proposal-plan": _TASK_MATERIAL_CONTEXT,
    "proposal-consistency": {**_SHARED_CONTEXT, "consistency": True},
    "paper-title-abstract": _SHARED_CONTEXT,
    "paper-framework": _TASK_MATERIAL_CONTEXT,
    "paper-expand-polish": _TASK_MATERIAL_CONTEXT,
    "paper-reference-format": _TASK_MATERIAL_CONTEXT,
    "paper-result-interpret": _TASK_MATERIAL_CONTEXT,
    "paper-reviewer-response": _TASK_MATERIAL_CONTEXT,
}
for _spec in AGENTS:
    _spec["context_scope_default"] = _CONTEXT_BY_KEY[_spec["key"]]


class Command(BaseCommand):
    help = "Seed K12 AI agent templates (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="用最新定义覆盖已有模板字段（key 不变）。",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        affected = 0
        for spec in AGENTS:
            key = spec["key"]
            defaults = {k: v for k, v in spec.items() if k != "key"}
            obj, created = AgentTemplate.objects.get_or_create(
                key=key, school=None, defaults=defaults
            )
            if created:
                affected += 1
            elif reset:
                for field, value in defaults.items():
                    setattr(obj, field, value)
                obj.save()
                affected += 1
        final_keys = {spec["key"] for spec in AGENTS}
        disabled = AgentTemplate.objects.filter(
            school=None, role=AgentTemplate.Role.STUDENT, is_active=True,
        ).exclude(key__in=final_keys).update(is_active=False)
        total = AgentTemplate.objects.filter(school=None).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"AI 模板就绪：本次新增/更新 {affected} 个，停用旧学生模板 {disabled} 个，全局模板共 {total} 个。"
            )
        )
