# Replicate UI Prototype

在修改 UI 布局、结构或信息层级前，先依据现有组件和设计 token 创建独立可交互的 HTML 原型；确认后再按原型数值落地到组件。

## 安装

```bash
git clone https://github.com/ChengxiuCDP/replicate-ui-prototype.git
cd replicate-ui-prototype
python3 scripts/install.py
```

默认安装到 `~/.codex/skills/replicate-ui-prototype`，也支持 `CODEX_HOME` 或 `--dest`。已有目录会自动备份。

## 使用

在 Codex 中调用 `$replicate-ui-prototype`，提供目标组件路径、截图或布局调整需求。完整流程见 [SKILL.md](SKILL.md)。

## 目录

- `SKILL.md`：触发条件、原型流程和落地约束。
- `agents/`：Codex 展示信息。
- `assets/`：HTML 原型模板。
- `references/`：框架适配与质量检查。
- `scripts/`：项目检查、原型校验、截图、本地预览、方向对比及安装工具。

## 可选发布

`scripts/publish.sh` 需要自行提供兼容的上传服务（接收 multipart `file` ZIP 文件，可用 `id` 更新）。仓库不提供公共托管服务。

```bash
UPLOAD_ENDPOINT="https://your-upload-service.example/upload" bash scripts/publish.sh prototype.html
```

脚本的参数和依赖请查看对应脚本的 `--help` 或源码。除发布地址配置外，上传内容保留本地 skill 的原始实现。
