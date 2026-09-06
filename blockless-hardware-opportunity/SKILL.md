---
name: blockless-hardware-opportunity
description: "将一句中文硬件创意转化为 Blockless 客户邮件、证据型 PDF 机会报告与递进式验证任务包。用于硬件创意的市场机会、早期需求信号和下一步验证；不用于承诺制造、销量、融资或投资回报。"
---

# Blockless Hardware Opportunity

为 Blockless 用户处理“一句话硬件创意”。默认产出中文，每次均生成完整客户版 PDF 和配套邮件草稿。目标不是替用户下结论，而是让一个想法在每次小确认后，更接近值得投入下一步的现实机会。

## 必须遵守的边界

- 将观察到的证据、推断和未知明确分开；禁止把热度、点赞、搜索量或 AI 新奇性说成付费需求。
- 不承诺免费制造、原型、融资、销量、成本、认证通过或收益。制造、工程与商业验证是三条独立轨道。
- 生成可供人工审核和发送的邮件草稿；不得擅自发送邮件、联系社区成员、提交表单或采集个人联系方式。
- 使用公开网络资料时遵守 robots.txt、网站条款和频率限制；保存 URL、日期、来源类型与短摘录。
- 可以把用户称为创意发起人或共同推进者，但不得隐瞒商业目的、虚构合作关系，或用情绪话术弱化不确定性。

## 工作流

1. 将一句话拆成使用者、使用时刻、目标结果、物理交互/形态、技术假设、购买/制造约束。缺失项标为未知；先做桌面研究，不要求用户补充后才开始。仅凭产品名和描述也必须执行此步骤，不得以品类词替代问题拆解。
2. 生成问题/结果、用户/场景、产品/替代、工程/供应链四组中英文检索词。读取 [关键词与问题空间](references/problem-space.md)。
3. 读取 `E:\startup-opportunity-validation` 的 `SKILL.md`、`references/framework.md`、`references/scoring.md`、`references/source-limitations.md`、`references/experiment-design.md`、`references/data-catalog.md`；查询 `knowledge-pack/` 和 `research/data/`。它们是跨类别行为信号引擎，不能替代本创意的硬件证据。
4. 对每个具体创意运行可复跑的公开采集：用 `scripts/collect_public_signals.py` 抓取 GitHub、Hacker News、Reddit 和经 robots 允许的种子页面；再运行 `scripts/cluster_signals.py` 去重、聚类和统计。不能联网或来源拒绝时，写入错误账本，不能假装“已爬取”。读取 [数据采集与聚类](references/data-pipeline.md)。
5. 按 [报告与评分](references/report-and-score.md) 输出市场线与工程线：用户、替代、证据账本、社区信号、评分、反证、风险与未知。分数只用于排序下一步实验。
6. 设计一份“共创路线图”，而不是“行动指导”。它严格递进：探索问题 → 选择用户/时刻 → 验证痛点 → 验证关键功能/原型 → 获取承诺 → 付费验证。每次只让用户完成当前一包；行动必须精确到目标地点/人群、任务、样本数、时间、强信号、kill rule，以及“完成后会解锁什么”。读取 [行动阶梯](references/action-ladder.md)。
7. 写作时同时运行“事实声道”和“愿景声道”。事实声道说清证据、未知与风险；愿景声道大胆描绘“如果它真的被做出来，谁的生活会改变、人与人会多出什么可能”，但必须明确写成愿景/假设，不能伪装成市场事实。读取 [人味与愿景写作](references/human-vision-writing.md)；可引用本 skill 的 `assets/writing-style-reference/` 压缩卡片。
8. 在生成客户邮件或 PDF 前，必须通过“研究门禁”（见下）。邮件结构、信任语言和任务包见 [客户沟通](references/client-communication.md)。客户报告通篇使用大白话：短句、具体人和具体时刻；技术评分放进“我们目前知道什么/还不知道什么”，不使用审计腔。用 PDF 技能生成并渲染检查后再交付。

## 强制研究门禁（不可跳过）

当用户只输入“产品名 + 描述”时，仍按以下顺序执行；不得直接写邮件正文、报告或泛品类检索。

1. 在 `output/<slug>/research-plan.json` 保存产品名、原始描述，以及 `user_scenarios`、`desired_outcomes`、`current_alternatives`、`product_form`、`engineering_constraints`、`commercial_constraints` 六组问题空间。每组至少一条；未知必须明确写作未知。
2. 在同一文件中生成至少 8 条英文定向检索词，覆盖至少 4 个问题空间维度。每条必须保存 `dimension`、`query`、`why`；其中至少一半是用户时刻、结果或替代方案词，不能全部是产品类别、品牌或技术词。
3. 用这些检索词运行公开采集和聚类。Reddit 默认不请求，仅在明确需要且端点可访问时附加 `--include-reddit`；它不能是主要证据来源。优先使用 Hacker News 的帖子与评论、GitHub、Stack Exchange、允许访问的官方社区、产品评论和一手来源。若 Reddit 或另一来源被拒绝，保留错误日志，并补充允许访问的公开来源；不可把失败来源计作覆盖。
4. 运行 `scripts/review_relevance.py --case-dir .\\output\\<slug>` 执行 Codex 自动相关性审核，并写入 `evidence/relevance-review.json`：至少 30 条与目标任务有关的记录，每条保留 `url`、`task_link`、`signal`、原始查询、实际查询变体和评分。自动审核按任务词与实际检索词的交集筛除无关记录；无关的新闻摘要、爬虫镜像、代码日报、纯技术 issue 必须排除。人工复核可选，但不得把词法相关性写成付费或采用证据。
5. 运行：

```powershell
python .\blockless-hardware-opportunity\scripts\validate_research_gate.py --case-dir .\output\<slug>
```

命令不是 `RESEARCH GATE: PASSED` 时，只能交付“证据不足/采集受阻”的内部说明，不能生成或更新客户邮件正文、PDF、评分或结论。通过后必须同时输出标准客户邮件 Markdown、人味版客户邮件 Markdown、共创路线图 Markdown、完整客户报告 Markdown 和客户报告 PDF；用 `scripts/render_client_pdf.py` 生成 PDF 时必须指定 `--preview evidence/pdf-render-preview.png`，再运行 `scripts/validate_client_delivery.py --case-dir .\\output\\<slug>`。PDF 生成、PNG 渲染预览和交付校验任何一项失败都不得交付。邮件中的每一个“我们看见”的断言都必须能回链到通过审阅的记录或一手来源。

## 每次交付

1. 邮件草稿：以 Blockless 的实验精神开场；让创意者感到自己不是“用户”而是项目的一部分；描绘远处的可能，再回到一个真诚、低摩擦的共同确认。情绪要真，不利用焦虑、孤独或 FOMO 施压。
2. 客户版 PDF：数据一个不少、证据优先、通篇大白话的 2–4 页分析。至少含问题空间、关键词、竞品/替代、具体社区/早期信号、市场/工程双线判断、风险、共创路线图与资料来源；所有数据都解释“它对这件事意味着什么”。
3. 内部证据附录：查询词、URL、时间、记录 ID、来源成功/失败、去重和聚类方式、未采用来源；默认不发送给用户。

## 决策标准

- 只在出现会议、数据共享、报价请求、预订、付费试点或付款等强行为时，建议进入商业验证。
- 若无强信号，修改用户、痛点、功能或价值主张；若核心痛点不成立，建议停止或换题。
- 对硬件始终单列 BOM、样机、交期、认证、可靠性、退货、支持与保修风险。市场信号不能自动清除工程风险。
