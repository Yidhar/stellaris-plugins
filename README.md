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

作者只在 `sources.jsonl` 里登记一次自己的仓库；`plugins.jsonl` 由 GitHub Actions **每小时自动生成**：取每个仓库的最新 Release，下载 zip、
读出其中的 `stl-plugin.json`、算出 SHA-256。所以发布新版本后，最多一小时索引里就是新版本，不需要再改这里。

`plugins.jsonl` 每行是一个插件：名称、作者、简介、版本、适配的游戏版本，以及它的 zip 在哪里、zip 的 SHA-256。本仓库**不存放任何二进制文件**：
插件的 zip 放在作者自己仓库的 GitHub Release 里，启动器下载后会先核对 SHA-256，再安装到
`文档\Paradox Interactive\Stellaris\plugins\<id>\`。插件规范见启动器的 [docs/PLUGINS.md](https://github.com/Yidhar/stellaris-launcher/blob/main/docs/PLUGINS.md)
和[开发手册](https://github.com/Yidhar/stellaris-launcher/blob/main/docs/PLUGIN_HANDBOOK.zh-CN.md)。

### 登记插件（只需一次）

1. 在你自己的公开 GitHub 仓库发一个 Release，附上一个 zip：根目录（或其中一个文件夹）里有 `stl-plugin.json` 和它写明的 DLL。
2. 在 `sources.jsonl` 里加一行，提一个 Pull Request：

   ```json
   {"repository":"https://github.com/你的用户名/仓库名","tags":["标签1","标签2"]}
   ```

   Release 里有多个 zip 时加 `"asset":"名字-v*.zip"`；作者名默认是仓库所有者，可以用 `"author"` 改。
3. CI 会取你的最新 Release 检查（zip、清单、DLL）。合并后，索引在一小时内出现你的插件。

**之后发新版本只要在你的仓库发 Release**，索引每小时自动跟上（维护者也可以在 Actions 里手动运行 `update`）。新 Release 不能用时（比如 zip 里没有清单），
索引保留上一个能用的版本，并在运行记录里报告。

想先看看索引会怎么写你的插件：`python scripts/plugin_entry.py <用户名/仓库名>`。

游戏更新后，在 `games.json` 里加一行新的 exe 时间戳 → 游戏版本，索引里就会显示插件适配的游戏版本号。

### 规则

- 源码公开，DLL 由这份源码构建；zip 只能来自 `repository` 所写仓库的 Release。
- 插件只在启动器加载时运行（不放代理 DLL、不自动加载），不修改游戏文件。
- 不收集个人信息、不联网上传数据（插件确需联网的，在简介里写明用途）。
- 一个仓库一个插件 id；`plugins.jsonl` 由自动任务生成，不要手改。

字段说明见 [schema/plugin-entry.schema.json](schema/plugin-entry.schema.json)。

## English

### What this is

Authors list their repository once in `sources.jsonl`; `plugins.jsonl` is **built every hour by GitHub Actions** from each repository's
latest release (the zip downloaded, its `stl-plugin.json` read, its SHA-256 worked out). A new release reaches the index within the hour,
with nothing to edit here.

Each line of `plugins.jsonl` is one plugin: its name, author, description, version, the game builds it is made for, and where its zip is
with the zip's SHA-256. **This repository holds no binaries**: a plugin's zip is an asset of a GitHub release of the author's own
repository; the launcher downloads it, checks the SHA-256, and installs it into `Documents\Paradox Interactive\Stellaris\plugins\<id>\`.
The plugin format is described in the launcher's [docs/PLUGINS.md](https://github.com/Yidhar/stellaris-launcher/blob/main/docs/PLUGINS.md)
and its [handbook](https://github.com/Yidhar/stellaris-launcher/blob/main/docs/PLUGIN_HANDBOOK.md).

### Listing a plugin (once)

1. Publish a release in your own public GitHub repository with a zip holding `stl-plugin.json` and the DLL it names, at its root or in one
   folder.
2. Add a line to `sources.jsonl` and open a pull request:

   ```json
   {"repository":"https://github.com/owner/repo","tags":["tag1","tag2"]}
   ```

   Add `"asset":"name-v*.zip"` when your releases have more than one zip; the author is the repository's owner unless `"author"` says
   otherwise.
3. CI checks your latest release (the zip, its manifest, the DLL). Once merged, the plugin is in the index within the hour.

**After that, a new release in your repository is all an update takes**: the index follows every hour (maintainers can also run the
`update` workflow by hand). When a new release cannot be used (no manifest in the zip, say), the index keeps the last usable version and
the run reports it.

To see what the index will say about your plugin: `python scripts/plugin_entry.py <owner/repo>`.

When the game updates, a line in `games.json` (the new exe timestamp → the game version) lets the index show the game version a plugin is
made for.

### Rules

- The source is public and the DLL is built from it; the zip comes only from releases of the line's `repository`.
- The plugin runs only when the launcher loads it (no proxy DLL, no autoload) and does not change the game's files.
- It collects no personal data and uploads nothing (a plugin that needs the network says what for in its description).
- One plugin id per repository; `plugins.jsonl` is written by the update workflow, not by hand.

The fields are described in [schema/plugin-entry.schema.json](schema/plugin-entry.schema.json).
