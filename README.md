# stellaris-plugins

[Stellaris Launcher](https://github.com/Yidhar/stellaris-launcher) 的 DLL 插件索引。启动器订阅本仓库的 `plugins.jsonl`，在「插件」页列出这里的插件，可以查看、下载安装和更新。

The index of DLL plugins for [Stellaris Launcher](https://github.com/Yidhar/stellaris-launcher). The launcher reads `plugins.jsonl` from
here and lists these plugins on its Plugins page, to look at, install and update. [English below](#english).

订阅地址 / Index URL:

```
https://raw.githubusercontent.com/Yidhar/stellaris-plugins/main/plugins.jsonl
```

## 中文

### 这是什么

`plugins.jsonl` 每行是一个插件：名称、作者、简介、版本、适配的游戏版本，以及它的 zip 在哪里、zip 的 SHA-256。本仓库**不存放任何二进制文件**：
插件的 zip 放在作者自己仓库的 GitHub Release 里，启动器下载后会先核对 SHA-256，再安装到
`文档\Paradox Interactive\Stellaris\plugins\<id>\`。插件规范见启动器的 [docs/PLUGINS.md](https://github.com/Yidhar/stellaris-launcher/blob/main/docs/PLUGINS.md)
和[开发手册](https://github.com/Yidhar/stellaris-launcher/blob/main/docs/PLUGIN_HANDBOOK.zh-CN.md)。

### 提交或更新插件

1. 在你自己的公开 GitHub 仓库发一个 Release，附上一个 zip：根目录（或其中一个文件夹）里有 `stl-plugin.json` 和它写明的 DLL。
2. 生成你的那一行（只需要 Python 3）：

   ```
   python scripts/plugin_entry.py <你的用户名/仓库名> --tags 标签1,标签2 --game-version 4.5.2
   ```

   Release 里有多个 zip 时加 `--asset '名字-*.zip'`。
3. 把输出的那一行加进 `plugins.jsonl`（更新时替换同一 id 的旧行），提一个 Pull Request。
4. CI 会下载 zip、核对 SHA-256，并检查其中的 `stl-plugin.json` 的 id、版本和游戏版本与这一行一致。通过并审核后合并，启动器就能看到。

本地检查：`python scripts/check_index.py`（加 `--offline` 只检查格式）。

### 规则

- 源码公开，DLL 由这份源码构建；zip 只能来自 `repository` 所写仓库的 Release。
- 插件只在启动器加载时运行（不放代理 DLL、不自动加载），不修改游戏文件。
- 不收集个人信息、不联网上传数据（插件确需联网的，在简介里写明用途）。
- 更新版本时同时更新这一行；一个 id 只有一行。

字段说明见 [schema/plugin-entry.schema.json](schema/plugin-entry.schema.json)。

## English

### What this is

Each line of `plugins.jsonl` is one plugin: its name, author, description, version, the game builds it is made for, and where its zip is
with the zip's SHA-256. **This repository holds no binaries**: a plugin's zip is an asset of a GitHub release of the author's own
repository; the launcher downloads it, checks the SHA-256, and installs it into `Documents\Paradox Interactive\Stellaris\plugins\<id>\`.
The plugin format is described in the launcher's [docs/PLUGINS.md](https://github.com/Yidhar/stellaris-launcher/blob/main/docs/PLUGINS.md)
and its [handbook](https://github.com/Yidhar/stellaris-launcher/blob/main/docs/PLUGIN_HANDBOOK.md).

### Adding or updating a plugin

1. Publish a release in your own public GitHub repository with a zip holding `stl-plugin.json` and the DLL it names, at its root or in one
   folder.
2. Make your line (Python 3 only):

   ```
   python scripts/plugin_entry.py <owner/repo> --tags tag1,tag2 --game-version 4.5.2
   ```

   Add `--asset 'name-*.zip'` when the release has more than one zip.
3. Put the line into `plugins.jsonl` (replacing the old line of the same id for an update) and open a pull request.
4. CI downloads the zip, checks its SHA-256, and checks that its `stl-plugin.json` has the line's id, version and game builds. Once it
   passes and is reviewed, it is merged and the launcher shows it.

Check locally with `python scripts/check_index.py` (`--offline` checks only the lines).

### Rules

- The source is public and the DLL is built from it; the zip comes only from releases of the line's `repository`.
- The plugin runs only when the launcher loads it (no proxy DLL, no autoload) and does not change the game's files.
- It collects no personal data and uploads nothing (a plugin that needs the network says what for in its description).
- Update the line with each release; one line per id.

The fields are described in [schema/plugin-entry.schema.json](schema/plugin-entry.schema.json).
