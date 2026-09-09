# 数据采集与聚类

每个创意的研究必须包含实时公开数据，而不仅是本地通用语料。默认运行：

```powershell
python scripts/collect_public_signals.py --queries "<英文问题词>,<英文产品词>" --output-dir .\tmp\signals
python scripts/cluster_signals.py --input .\tmp\signals\raw-signals.jsonl --output-dir .\tmp\clusters
```

## 采集标准

- 目标是每个查询在 GitHub、Hacker News、Stack Exchange 三类公开社区中各取最多 100 条结果（Reddit 只在 `--include-reddit` 时补充）；再补至少两类一手产品/竞品/标准来源。限速、缓存、记录 HTTP 失败，不绕过登录、验证码、付费墙或 robots。
- 检索词永远按原句搜；超过 3 个实词时额外搜末尾两个二元组，但二元组只是补充，不能替代原句。GitHub 搜索未登录时每分钟 10 次，`--max-workers 1 --pause-seconds 7` 最稳。
- Stack Exchange 用 `--stackexchange-sites` 指定站点，选创意的用户真正提问的社区（电子类 electronics、DIY 类 diy、育儿类 parenting……）；站点选错会整段为空，且未登录配额每天 300 次，站点不要超过 6 个。
- 不收集个人邮箱、电话、私信、账户画像或封闭社区内容。公开帖子用于问题证据，不自动变成营销名单。
- 每条记录必须保留来源、社区、URL、时间、查询词和抓取时间。采集器不做网页表单交互。
- 种子 URL 仅用于官方产品、标准机构、众筹/零售公开页面或用户明确指定的公开页面；先检查 robots，再限速抓取正文和标题。

## 聚类标准

1. 按 canonical URL 和标准化标题精确去重；记录原始数、唯一数和去重率。
2. 用 TF-IDF + MiniBatchKMeans 对标题和摘要聚类；聚类数在 `max(3, min(12, round(sqrt(唯一记录数))))` 内选择。
3. 每簇报告记录数、来源/社区数、代表链接、重复任务、替代方案、价格/采购/自制/支持等强信号数和反证。
4. 不把聚类标签当结论。人工检查至少前三个簇和所有价格、采购、维修、退货、预订记录。

## 最小证据门槛

桌面研究阶段要求至少：30 条唯一公开记录、3 个不同来源或社区、5 条可点击代表链接，以及一条明确的反证/替代证据。达不到时，报告应写“证据不足”，并解释是检索词、来源、地域还是市场本身的问题。
