# Blockless Hardware Opportunity Validation

本仓库包含 `blockless-hardware-opportunity` skill：将一句中文硬件创意转化为客户邮件草稿、证据型 PDF 机会分析和逐阶段验证任务包。

它依赖 `E:\startup-opportunity-validation` 的压缩知识包、评分框架及溯源数据；不复制原始 3GB+ 资料，也不会自动发送邮件或承诺制造。

## 强制研究流程

只输入产品名与描述时，skill 先生成问题空间、核心词和定向检索计划，再采集、聚类并审核相关记录。没有通过研究门禁，不允许生成客户邮件正文或机会报告。门禁检查命令：

```powershell
python .\blockless-hardware-opportunity\scripts\validate_research_gate.py --case-dir .\output\<产品-slug>
```

门禁通过后，四份交付先写成带 `[n]` 引用编号的内部版，由一个没参与写作的核对者逐条对照记录原文（结果记入 `evidence/citation-review.md`），干净之后才剥掉编号生成发送版并渲染 PDF；交付校验会拒绝没有核对记录、发送版与内部版不一致或含研究黑话的案例。规则见 `blockless-hardware-opportunity\references\citation-review.md`。

另外包含一个由 10,000 条授权中文创作参考单元压缩而成的“人味与愿景写作”库，位置在 `blockless-hardware-opportunity\assets\writing-style-reference\`。它会随 skill 安装；只用于指导叙事节奏、具体感和共同推进的语气，不用于复制原文或把愿景写成事实。原始本地语料的来源与分发边界见 [corpus/SOURCES.md](corpus/SOURCES.md)。

本地证据匹配工具：

```powershell
python .\blockless-hardware-opportunity\scripts\match_local_evidence.py `
  --keywords "smart lock,home safety,access" `
  --output .\tmp\evidence.json
```

## 运行环境

使用 Python 3.10+，首次运行聚类或语料压缩脚本前执行：

```powershell
python -m pip install -r .\requirements.txt
```

`tmp/`、`output/` 和下载的原始语料均为本地工作文件，不纳入版本库；skill 自身所需的压缩写作参考库位于 `assets/`，会被提交和安装。

## Blockless 的核心交付要求

每一份交付都同时做到三件事：

1. **严谨，但不说黑话。** 数据、采集量、来源、竞品、评分、反证、工程风险一个不能少；每个数字后必须解释“这对这个创意意味着什么”。事实、推断和未知清楚分开。
2. **大胆，但不把愿景说成事实。** 愿景部分从“如果这件事真的实现，谁的生活会有什么不同”往远处推；使用“如果、也许、我们想象”，永远留下一点诚实的未知。
3. **让创意发起人成为共同作者。** Blockless 想做的实验是：如果创造产品不再要求你先成为工程师，这个世界会多出多少原本不会存在的东西？路径是“这个世界是不是应该有……”→ 找到相信它的人 → 一起证明它 → 看着它第一次出现在现实世界。

固定交付为：

- **机会报告**：2–4 页，大白话、有数据、有内容；不砍事实，不写审计腔。
- **共创路线图**：不叫“行动指导”；每一步写明去哪里、找谁、做什么、样本数、指标、停止条件和完成后会解锁什么。
- **邮件**：先让人看见一个值得相信的未来，再回到一个真诚的小邀请。情绪要真，不利用焦虑、孤独、FOMO 或虚假承诺施压。
