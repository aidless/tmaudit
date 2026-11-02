# 预注册规格（Preregistration）— tmaudit

> 本文件是 **tmaudit 的预注册/规格文档**，声明本工具在真实代码里检验的
> 研究假设、评测方案与成功标准，以及**明确的证明边界**。
> 一切陈述均对应仓库内真实可复算的实现（`src/tmaudit/`、`tests/`、
> `case-studies/`、`docs/`）。

## 1. 研究问题（本工具回答什么）

**研究问题**：能否用一个**固定的、可配置的报告完整性规则包**（C1–C10），在
LaTeX 源码上**自动**抓出机器学习论文投稿中最常见、最容易在同行评审被点名的
**报告缺陷**——缺失 code/data 可用性声明、未报告随机种子与超参、定义却从未
被引用的 figure、仪式性引用、无功效分析却作显著性声明——而**不需要 API key、
不需要网络、不需要任何第三方依赖**（Python 3.9+ 标准库，或零安装单文件
`.pyz`）？

这个问题是**真问题**：这些缺陷修复成本低（改几行），但投稿前人工发现成本高。
本工具在投稿前自动抓出它们。

## 2. 先验假设（声明：验证什么，不验证什么）

- **H1（固定规则包可检测报告缺陷）**：C4–C10 在**任意** LaTeX 稿件上运行；
  C1–C3 与 C6 由 per-paper 配置驱动，配置不适用的类别**明确报告
  `not applicable`，而非静默当作通过**。
- **H2（"零发现"不等于"通过"）**：一个类别报告零发现，**除非它真的运行过**，
  否则不是通过。配置驱动的类别未运行时打印
  `[not applicable: no per-paper config]`。
- **H3（工具自审计）**：把审计核心跑在 **25 篇真实 arXiv `cs.CL` LaTeX 源**上，
  暴露工具自身缺陷并全部修复。

### 成功标准（可复算）

| 假设 | 成功判据 | 复算入口 |
|------|---------|---------|
| H1 | C4–C10 任意稿件可跑；C1–C3/C6 配置不适用时明确报告 not applicable | `python -m pytest -q`（264 passing + 3 skipped，2026-11-01） |
| H2 | 未运行类别不静默通过，输出 `[not applicable]` 而非零发现 | 同上 + `examples/run_demo.sh` |
| H3 | 25 篇语料发现 4 处工具缺陷（config leak / "clean"=没跑 / KeyError / BibTeX pattern bug），全部修复于 v0.5.1 并带回归测试 | `case-studies/arxiv-corpus/README.md` |

## 3. 评测方案（如何判定成功）

**单元 + 集成测试**（`python -m pytest -q`）：**264 passing + 3 skipped**
（2026-11-01），分布在 `tests/test_forge_happy.py`、
`tests/test_bug5_unit.py`、`tests/test_c6_threshold.py`、
`tests/test_c7_citation_context.py`、`tests/test_cache.py`、
`tests/test_c10_reproducibility.py`、`tests/test_c8_statistical_power.py`、
`tests/test_c9_figure_caption.py`。

**meta-test**（`_check_all_regressions.py`）：注入每个历史 bug，断言回归测试
抓到它，再恢复源码——**14/14 bugs 被捕获**。

**60 秒 demo**（`bash examples/run_demo.sh`）：故意有缺陷的样稿返回
**6 findings（1 medium, 5 low）**，工作树保持不变。

**25 篇 arXiv 自审计**（`case-studies/arxiv-corpus/`）：25/25 篇 cs.CL 源码，
每个类别与 `verify_TEMPLATE.main()` 完全一致的调用方式；发现工具自身 4 处缺陷
（D1 工厂 config 泄漏、D2 "clean"=没跑、D3 KeyError 中止整审、D4 BibTeX key
模式伪造缺失引用），全部修复于 v0.5.1 并带回归测试。

**单篇真实稿件验证**（`case-studies/arxiv-2502.14074/`）：对
*Investigating Non-Transitivity in LLM-as-a-Judge*（arXiv:2502.14074，ICML 2025）
跑两条公开扩展路径，报告 2 项报告标准观察、记录 3 个被检查后**撤回**的候选
弱点，并暴露一个 caption 解析缺陷（嵌套花括号），已修复。每个输入以 SHA-256 固定。

## 4. 质量门与规则包（真实值）

规则包共 10 类（C1–C10）+ C7-LLM 可选回退，见 README 表格：

| 类别 | 检查内容 | 严重度 | 是否总运行 |
|------|---------|--------|-----------|
| C1 (v0.1.0) | 符号内联定义 | HIGH | 是 |
| C2 (v0.1.0) | Bonferroni 一致性 | HIGH | 是 |
| C3 (v0.1.0) | 关键概念形式化 | MEDIUM | 是 |
| C4 (v0.1.0) | 自引阈值 | MEDIUM | 是 |
| C5 (v0.1.0) | 测试名 d | MEDIUM | 是 |
| C6 (v0.1.1) | 黑名单词频 | LOW | 是 |
| C7 (v0.1.2) | 仪式性引用检测 | MEDIUM | 是 |
| C8 (v0.3.0) | **统计功效**（d 失配、post-hoc power） | HIGH/MED | 否（opt-in） |
| C9 (v0.3.0) | **图注一致性**（4 子检查） | HIGH/MED | 是（子检查 3 opt-in） |
| C10 (v0.3.0) | **可复现性**（可用性、元数据、一致性） | HIGH/MED/LOW | 是（子检查 2 opt-in） |
| C7-LLM (v0.2.0) | C7 边界情况的 LLM 回退（`TMAUDIT_LLM_*` env） | MEDIUM | 否 |

## 5. 明确边界（证明什么 / 不证明什么）

**本工具证明（可复算）：**

1. 一个固定规则包（C1–C10）能在 LaTeX 源码上抓出报告完整性缺陷，零外部依赖、
   零网络、零 API key。
2. 配置驱动类别的"未运行"状态被**明确报告**而非静默通过（fail-closed）。
3. 工具自身在 25 篇真实语料上暴露 4 处缺陷并全部修复（自审计闭环）。
4. `verify` 会 fork 一个可编辑的 `verify_generic.py` 到目标目录——工具是
   "开放源码"的字面意义：你能读、能改它检查什么。

**本工具不证明（边界）：**

- **不是审稿人，不评判新颖性**——它只按固定规则包检查报告完整性，不判断
  科学是否正确。
- **一个类别报告零发现不是通过**，除非它真运行过；配置驱动类别未运行时打印
  `[not applicable: no per-paper config]`。
- **25 篇语料自审计不建立规则包泛化到整个 `cs.CL` 的结论**——它是语料探针，
  不是证明（见 case-study README 对"数字证什么不证什么"的说明）。
- **demo 的 6 个发现描述的是故意有缺陷的样稿**，不是对真实稿件的声明。

## 6. 已知限制

- `.pyz` 单文件分发（64 KB）只依赖 Python 标准库，兼容 Linux / macOS / Windows。
- PyPI 0.5.1 是上一发布版；仓库是 0.5.2（用 git URL 装当前源码）。
- 12 个历史 bug 每个都有对应回归测试；meta-test 注入每个 bug 断言回归测试捕获。
