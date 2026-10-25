# TestPyPI 上传 — 自助执行手册（v0.7.0）

本文档给你直接复制粘贴的命令。token 由你自己输入，不进对话记录。

**当前状态**：产物已构建并通过本地全量验证，尚未上传任何索引。

---

## 0. 先决条件（1 分钟）

需要 **TestPyPI 专用 token**，与 PyPI token 不通用。

1. 打开 https://test.pypi.org/manage/account/token/
2. 若从未建过：点 "Add API token"，Scope 选 **Entire account**（首次上传必须，因为项目尚不存在，无法限定到项目）
3. 复制 `pypi-` 开头的字符串

> 注意：TestPyPI 与 PyPI 是两套独立账号。如果你在 TestPyPI 上没注册过，需先用与 PyPI 相同的邮箱注册并验证。

---

## 1. 上传到 TestPyPI

```bash
cd /home/liuzewen/project-review-20261013/verify/tmaudit

/home/liuzewen/.workbuddy/binaries/python/envs/default/bin/python -m twine upload \
  --repository-url https://test.pypi.org/legacy/ \
  --username __token__ \
  --password 'pypi-这里粘贴你的TestPyPI_token' \
  dist/*
```

**预期输出**（关键行）：

```
Uploading tmaudit-0.7.0-py3-none-any.whl
Uploading tmaudit-0.7.0.tar.gz
View at:
https://test.pypi.org/project/tmaudit/0.7.0/
```

**若报错**：

| 报错 | 原因 | 处置 |
|---|---|---|
| `403 Invalid or non-existent authentication` | 用了 PyPI 的 token，不是 TestPyPI 的 | 回 §0 重新取 TestPyPI token |
| `400 File already exists` | 该版本此前传过 | 无法覆盖。把 `pyproject.toml` 版本改成 `0.7.0.post1` 后重新 build |
| `SSL: CERTIFICATE_VERIFY_FAILED` | 代理/证书问题 | 见 §5 |

---

## 2. 从 TestPyPI 安装并验证

**关键点**：必须带 `--extra-index-url https://pypi.org/simple/`。因为 `tmaudit` 的依赖虽然为空，但 pip 解析时若只给 TestPyPI 索引会遇到同名包冲突；带 extra 索引是官方推荐做法。

```bash
rm -rf /tmp/tp-verify
/home/liuzewen/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m venv /tmp/tp-verify

/tmp/tp-verify/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "tmaudit==0.7.0"
```

**必须确认 pip 是从 test.pypi.org 下载的**，输出里应出现：

```
Downloading https://test-files.pythonhosted.org/packages/.../tmaudit-0.7.0-py3-none-any.whl
```

如果显示的是 `files.pythonhosted.org`（无 `test-` 前缀），说明装到了 PyPI 上的旧版或缓存，**不是**你要验证的东西。

### 三项功能验证

```bash
/tmp/tp-verify/bin/tmaudit --version
# 期望: tmaudit 0.7.0

/tmp/tp-verify/bin/tmaudit admission --gain 7.3 --tasks 89
# 期望: [NOT CERTIFIED] gain=+7.30pp  upper=+32.10pp  m=89 ...
#       note: certifying this gain would need tasks m >= 2,593
#       退出码 1

/tmp/tp-verify/bin/tmaudit admission --required-tasks 7.3
# 期望: tasks m >= 2,593
#       退出码 0
```

### 外部 target 端到端（这是 0.6.0/0.7.0 的核心能力）

```bash
mkdir -p /tmp/tp-ext && cd /tmp/tp-ext

cat > main.tex <<'TEX'
\documentclass{article}
\begin{document}
\title{A Paper Nobody Owns}
\author{Someone Else}
\maketitle
\begin{abstract}
We test whether an external config can drive the verify path.
\end{abstract}
\section{Introduction}
Recent work has studied this problem \cite{smith2020}.
\section{Method}
We extend the framework of Smith et al. \cite{smith2020,doe2021}.
\section{Experiments}
Results follow.
\section{Conclusion}
Done.
\end{document}
TEX

cat > refs.bib <<'BIB'
@article{smith2020, title={A Study}, author={Smith, John}, journal={J}, year={2020}}
@inproceedings{doe2021, title={Another}, author={Doe, Jane}, booktitle={C}, year={2021}}
BIB

cat > paper.toml <<'TOML'
schema = "tmaudit-target/1"

[paper]
name = "externally-owned"
tex_basename = "main"
bib = "refs.bib"
TOML

/tmp/tp-verify/bin/tmaudit verify --target paper.toml
# 期望: 尾部 "TOTAL: 5 findings (HIGH=0, MEDIUM=0, LOW=5)"
#       "[WRITE] .../verify_externally-owned.py"
#       退出码 0
```

---

## 3. 上传到正式 PyPI（仅在 §2 全部通过后）

```bash
cd /home/liuzewen/project-review-20261013/verify/tmaudit

/home/liuzewen/.workbuddy/binaries/python/envs/default/bin/python -m twine upload \
  --username __token__ \
  --password 'pypi-这里粘贴你的PyPI_token' \
  dist/*
```

不带 `--repository-url` 时 twine 默认走 `https://upload.pypi.org/legacy/`。

**不可逆**：`0.7.0` 这个版本号一经上传无法撤回或复用，只能发 `0.7.1`。

---

## 4. 上线后核对

```bash
# 元数据是否同步（传播约需 1 分钟）
curl -s https://pypi.org/pypi/tmaudit/json | \
  /home/liuzewen/.workbuddy/binaries/python/envs/default/bin/python -c \
  "import json,sys; d=json.load(sys.stdin); print(d['info']['version']); print(list(d['releases']))"
# 期望: 0.7.0 / ['0.5.0', '0.5.1', '0.7.0']
```

页面：https://pypi.org/project/tmaudit/0.7.0/

---

## 5. 已知坑

**SSL 证书错误**：若 `CERTIFICATE_VERIFY_FAILED`，先确认是否走了代理：

```bash
echo $HTTPS_PROXY
# 若用了自签证书代理，追加 --cert 指向 CA bundle，或临时 unset 代理
```

不要用 `--disable-ssl-verify` 之类的绕过手段上传——凭据会明文穿过不受信的 TLS 层。

**twine 版本差异**：本仓 twine 为 7.0.0，`--repository`（不带 url）已废弃，必须用 `--repository-url`。上面命令已按 7.x 写。

**token 作用域**：首次上传后，建议回 TestPyPI 删除整个账号级 token，改用限定到 `tmaudit` 项目的 token。

---

## 6. 执行完后

把 §2 的三段输出（或报错原文）发我，我据此更新 `RELEASE_CHECKLIST.md` 的 §6 状态并落记忆。

另外两件未决事项：

- **git tag 尚未打**。提交 `3d78dc7`、`e5bdc23` 都在本地，未 push。
- **GitHub 远端**：`pyproject.toml` 里写的是 `github.com/aidless/tmaudit`，上传后 PyPI 项目页会链过去。若远端实际没有 push，用户点进去会看到 404——发布前建议先 push。
