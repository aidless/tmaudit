# Case study: tmaudit's audit core on 25 real arXiv papers

`tmaudit` is published on PyPI, and its README tells a reader to fork the
template into their own paper directory and edit the `CHECKS_CONFIG` block. This
case study asks the question a "clone and run" reader will ask: **what does the
audit core actually do on real papers?**

Answer: on 25 real cs.CL papers run as shipped, it produces one HIGH finding on
**25 of 25**, reports two categories as clean **without having checked
anything**, and — on a paper with a perfectly ordinary `.bib` — invents missing
citations that are present in the file. Four defects, each reproduced here with
the evidence.

This is not a claim that the rulepack is wrong. Its categories are a per-paper
rulepack and were built for five specific papers. What is measured below is the
*configuration surface*: what a reader gets when they do what the README says
and what the tool does when its assumptions do not hold.

> **Status: fixed in v0.5.1.** The audit below was run against the template
> **as shipped in v0.5.0** and its findings are preserved as evidence. All four
> defects plus the two smaller things were fixed in v0.5.1 (see the repo
> CHANGELOG): the factory config is now empty with paper-specific categories
> reporting *not applicable*, the summary distinguishes checked / not
> applicable / error, one crashed check no longer aborts the audit, the bib-key
> regex is relaxed with regression tests, the docstring is raw, and C1's
> missing-abstract observation is filed as an error instead of a HIGH finding.
> Running `audit_corpus.py` against a v0.5.1+ template restores the v0.5.0
> factory config, so the config-driven defects (D1/D2/D3) replay as recorded;
> the D4 regex fix and D6's re-filing live in the function bodies, so a re-run's
> C1 and C4 rows differ, as documented in the script.

## Coverage matrix: 25 papers, 10 categories

Corpus: the first 25 entries of arXiv's `cs.CL` recent listing at run time, taken
in page order, no content screening. 25 of 25 shipped LaTeX sources. Every
category was invoked exactly as `verify_TEMPLATE.main()` invokes it — same
order, same arguments, same shipped default config — with one difference: this
harness wraps each check in a `try`, and that difference is defect 3.

| category | fired | clean | what the clean ones mean |
|---|---:|---:|---|
| C1 abstract symbols | 2 | 23 | both "fires" are `No abstract environment found.`, not symbol findings |
| **C2 Bonferroni** | **25** | 0 | **100% false positive** — the config demands the author's Paper-1 "Power analysis" section |
| **C3 formalisation** | 0 | **25** | **vacuous** — returns empty when its configured concept token is absent |
| C4 citation hygiene | 14 | 11 | includes fabricated "missing cite key" findings (defect 4) |
| C5 sample size / test | 0 | 25 | **true negatives** — verified independently |
| C6 blacklist vocabulary | 16 | 9 | objective, but the word list is an author style preference |
| C7 ceremonial citations | 23 | 2 | threshold- and regex-bound; volume suggests a coarse detector |
| **C8 statistical power** | 0 | **25** | **vacuous** — `c8_claimed_effects` is empty for every paper |
| C9 figure captions | 15 | 10 | contains a genuinely useful, config-independent sub-check |
| C10 reproducibility | 24 | 1 | config-independent sub-checks; plausible but coarse |

## Defect 1 — the shipped config is one specific paper's config

The template's default `CHECKS_CONFIG` is not neutral. Read out of the file:

| key | shipped value |
|---|---|
| `c1_symbols` | `CAF`, `E_T`, `ΔECE`, `TTRL` — four symbols from Paper 1 |
| `c2_section_pattern` | a section literally titled "Power analysis" |
| `c3_concept_token` / `c3_formal` | `Face 1` / `\section{Face 1:` |
| `c4_self_cite_prefix` | `liu2026` |
| `c6_blacklist` | `paradigm`, `yield`, `reveal` |

Consequence, measured: C2 fires on **25 of 25** papers with

```
HIGH  C2  No Power analysis section declaring Bonferroni k found. Reviewer §3 #4.
```

A reader who forks this template and runs it gets a HIGH-severity finding shaped
by someone else's paper. The fix is not subtle: ship a neutral default (empty
lists, no section pattern) and let each category report `not applicable` instead
of firing on a foreign config.

## Defect 2 — "clean" that does not mean "checked"

Three categories can report zero findings without having examined anything:

* **C3** — `if not concept_token or not formal_pat: return findings`, then
  `re.search(concept_token, tex)`; when a paper does not contain the configured
  concept token it returns the empty list. Across the corpus that produced **25
  "clean"** results. "Clean" there means *this paper does not contain the
  concept my config names*, which is not a statement about the paper.
* **C8** — `check_c8_statistical_power(tex, c8_claimed_effects)`: with an empty
  claim list there is nothing to check, and it reports 0 findings on all 25.
* **C1** — `if not cfg_syms: return []`. Same shape.

This is the failure mode the project's own mutation-control exists to catch: a
gate that reports green while proving nothing. It is worth fixing in the tool
for the same reason it was worth catching in the CI gates.

## Defect 3 — one missing config key aborts the whole audit

`main()` calls the ten checks consecutively with no isolation, and several
categories hard-index the config (`CHECKS_CONFIG['c2_families']`,
`['c4_self_cite_threshold']`, `['c1_symbols']`). Demonstrated directly:

```
>>> CHECKS_CONFIG.clear()
>>> check_c2_bonferroni_consistency(tex)
KeyError('c2_families')
```

There is no try/except anywhere in `main()`, so one absent key ends the audit
rather than reporting one category as unavailable. This harness had to add
per-check isolation to produce the matrix above at all; run as shipped, the audit
would have died on the first paper that lacked a configured key.

## Defect 4 — the bib-key pattern invents missing citations

`check_c4_citation_hygiene` extracts bib keys with

```python
bib_keys = set(re.findall(r'@\w+\{([^,]+),', bib))
```

`[^,]+` swallows the newline when a `.bib` puts the key on its own line — a
common export style. Reproduced on paper `2610.22324`, whose `.bib` contains

```
@inproceedings{
dubois2404length,
title={...
```

C4 reported `6 cite key(s) in main.tex missing from refs.bib`, including
`dubois2404length`. All three sampled keys **are present in that file**; the
strict pattern misses them because the captured string is `"\ndubois2404length"`.
Relaxing it to `@\w+\{\s*([^,\s]+)\s*,` recovers all three. So C4's 14 firings
include a class of fabricated findings, and the pattern is the cause.

The same check also reads its self-cite threshold from `CHECKS_CONFIG`, and its
shipped prefix is `liu2026` — another author-specific value pointed at foreign
papers.

## What is portable, and worth keeping

Two categories contain sub-checks that need no per-paper config and produced
concrete, checkable findings on real papers:

* **C9** — `figure fig:compaction-prompt is defined but never referenced in the
  body text`. That is a real consistency defect and it is exactly the kind of
  thing a mechanical gate should catch.
* **C10** — `no hyperparameters reported (no "learning rate", "batch size", or
  "optimizer" found)`, plus availability-statement checks. Coarse, but it is
  reading the paper rather than the config.

And one verified **true negative**, which matters as much as a hit: C5 fired zero
times, and it is correct to. Of the 20 abstracts locatable by direct regex on the
un-flattened main files, **none contains a p-value or a `d=` value**, so there
was nothing for C5 to report. A gate that stays quiet when there is nothing to
say is working.

## Two smaller things

* Importing the shipped template emits
  `SyntaxWarning: invalid escape sequence '\c'` at `verify_TEMPLATE.py:1494` — a
  docstring escape that should be raw.
* C1 files `No abstract environment found.` under category **C1**, whose declared
  severity is HIGH and whose stated purpose is "abstract symbol definitions". A
  missing abstract is not a symbol-definition problem; the finding is correctly
  noticed and wrongly filed.

## Method, and what this does not establish

* **Corpus**: mechanical. `ids.txt` is committed; the selection rule is "first 25
  entries of the cs.CL recent listing, page order" and it was not curated after
  seeing any result.
* **Preprocessing**: the harness flattens `\input`/`\include` and picks the
  paper's named `.bib` (falling back to the largest). Every C4 finding was
  hand-checked against the raw file before being called fabricated — which is how
  defect 4 was found rather than blamed on the harness.
* **Not established**: that the categories are badly designed, or that these 25
  recent preprints are representative. The categories are a per-paper rulepack,
  and the honest reading of defect 1 is "the default is a specific paper's
  config", not "the rules are wrong".
* The tool's intended workflow — a config written for the paper under audit —
  none of this corpus has. What is measured is the shipped-default surface.

## Reproduce

```bash
python3 audit_corpus.py --prepare   # unpack the e-prints in _corpus/
python3 audit_corpus.py             # audit and write results.json
```

`_corpus/` is git-ignored; `ids.txt` and `results.json` are committed, so the
matrix above can be read without downloading 100 MB of arXiv sources.

---

# 中文部分

**这是对你上 PyPI 那个包的审计，对象是「一个读者照 README 说的把模板 fork 到自己论文上」时的真实体验。** 语料是 arXiv `cs.CL` 最新 listing 的前 25 篇（按页面顺序，不做内容筛选，25/25 都有 LaTeX 源），十类检查按 `main()` 完全相同的方式调用。

| 类别 | 触发 | 通过 | 「通过」的真实含义 |
|---|---:|---:|---|
| C1 符号定义 | 2 | 23 | 两次触发的消息都是 `No abstract environment found.`，**不是符号问题** |
| **C2 Bonferroni** | **25** | 0 | **100% 假阳性**——配置要求作者 Paper-1 的 "Power analysis" 章节 |
| **C3 形式化** | 0 | **25** | **空转**——配置里的概念 token 不存在时直接返回空 |
| C4 引用卫生 | 14 | 11 | 含**伪造的「引用缺失」**（缺陷 4） |
| C5 样本量/检验 | 0 | 25 | **真阴性**——独立核验确认 |
| C6 词表 | 16 | 9 | 客观，但词表是作者的文风偏好 |
| C7 礼节性引用 | 23 | 2 | 阈值与正则绑定，触发量提示判定偏粗 |
| **C8 统计功效** | 0 | **25** | **空转**——`c8_claimed_effects` 对所有论文都是空 |
| C9 图题 | 15 | 10 | 含**真正有用**的免配置子检查 |
| C10 可复现性 | 24 | 1 | 免配置子检查；合理但偏粗 |

**四个已验证的缺陷（均附实证）**：

1. **出厂默认配置就是某一篇特定论文的配置**。`c1_symbols` 是 `CAF/E_T/ΔECE/TTRL`，`c2_section_pattern` 要求一个叫 "Power analysis" 的章节，`c3_formal` 要求 `\section{Face 1:`，`c4_self_cite_prefix` 是 **`liu2026`**。后果：**C2 在 25/25 篇上全部报 HIGH**。任何人 fork 这份模板去审自己的论文，拿到的是**别人论文的结论**。
2. **「通过」不等于「检查过」**。C3 在配置里的概念 token 不存在时 `return` 空列表（本语料 25/25 都走了这条路）；C8 在 claims 为空时无物可查；C1 在 `c1_symbols` 为空时同样 `return []`。**这正是你项目自己的 mutation-control 专门要抓的失效模式——一道报绿却没证明任何事的门。**
3. **一个缺失的配置键会让整篇审计崩掉**。`main()` 顺序调用十个检查、**毫无隔离**，而 C2/C4/C1 用硬索引取配置。直接实证：清空配置后 `check_c2_bonferroni_consistency` 抛 `KeyError('c2_families')`。**本审计的脚本之所以能产出这张表，就是因为我给每个检查加了 try——按出厂状态跑，第一张缺键的论文就会中断。**
4. **bib key 正则会凭空造出「缺失引用」**。`@\w+\{([^,]+),` 中的 `[^,]+` 会吞掉换行，于是 key 单独放一行的 `.bib`（常见导出风格）被误判。实证：`2610.22324` 的 `.bib` 里三个被报「缺失」的 key **全部实际存在**，把正则放宽为 `\s*([^,\s]+)\s*,` 后全部命中。

**仍然值得保留的部分**：C9 的「图被定义但正文从未引用」、C10 的「未报告任何超参 / 可用性声明」都是**免配置且真实**的检查，在本语料上给出了具体可核的结论。另外 **C5 的零触发是经过独立核验的真阴性**（能定位到的 20 篇摘要中，0 篇含 p 值或 `d=`）——**一道在无话可说时保持安静的门是在正常工作**。

**两处小问题**：导入该模板会打印 `SyntaxWarning: invalid escape sequence '\c'`（`verify_TEMPLATE.py:1494` 的文档字符串未用 raw）；C1 把「未找到 abstract 环境」记在 **C1** 名下，而 C1 声明为 HIGH、职责是「摘要符号定义」——问题被正确发现、被错误归类。

**方法与不成立的推论**：语料是机械选取的（规则写在 `ids.txt` 旁、未按结果筛选）；预处理会展开 `\input` 并选取论文自述的 `.bib`，**每条 C4 结论都先与原始文件手工比对过才判定为伪造**——缺陷 4 正是这样找出来的，而不是推给预处理。**不成立的推论**：说这些类别设计得不好，或说这 25 篇近期预印本有代表性。它们是**逐篇配置的规则包**，缺陷 1 的诚实表述是「默认值是某一篇的配置」，而不是「规则是错的」。

> **状态：上述缺陷已在 v0.5.1 修复。** 本审计针对 **v0.5.0 出厂状态**运行，结果作为证据保留。四个缺陷与两处小问题全部修复（见仓库 CHANGELOG）：出厂配置改为空表、逐篇配置类别改报 *not applicable*、汇总区分 checked / not applicable / error、单个检查崩溃不再中断整篇审计、bib key 正则放宽并附回归测试、文档字符串改 raw、C1 的无摘要观测改记为 error 而非 HIGH finding。在 v0.5.1+ 模板上重跑 `audit_corpus.py` 会自动恢复 v0.5.0 出厂配置，配置驱动的缺陷（D1/D2/D3）按原样复现；D4 的正则修复与 D6 的 C1 改归类在函数体内，重跑的 C1/C4 两行会不同——脚本内有说明。
