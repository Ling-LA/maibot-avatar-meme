# QQ头像表情包 | Avatar Meme 🎀

一个 [MaiBot](https://github.com/Mai-with-u/MaiBot) 插件，通过 `/表情` 命令用 QQ 号或 @某人 的头像生成搞笑表情包。

> 🎨 调用 [apix.iqfk.top](https://apix.iqfk.top) 聚合 API，支持 **329 种**单人效果（V1）+ **18 种**双人效果（V2）。

## ✨ 功能

- 🎭 **V1 单人表情包**：329 种效果，用 1 个 QQ 号的头像生成
- 👥 **V2 双人表情包**：18 种效果，用 2 个 QQ 号的头像生成
- 📋 **图片菜单**：`/表情列表` 和 `/表情2列表` 分页浏览所有效果
- 🔍 **灵活匹配**：支持序号、完整名称、关键词模糊匹配
- 🏷️ **@自己**：`@自己` 自动解析为发送者 QQ（无需手动输入）
- 💾 **效果缓存**：每日自动同步最新效果列表

## 📥 安装

```bash
cd MaiBot/plugins
git clone https://github.com/Ling-LA/maibot-avatar-meme.git
```

或直接下载 zip 解压到 `MaiBot/plugins/ling_avatar-meme/`。

## ⚙️ 配置

编辑插件目录下的 `config.toml`：

```toml
[plugin]
enabled = true
config_version = "3.3.0"
api_key = "你的V1_API_KEY"      # 用于单人效果（sv1）
api_key_v2 = "你的V2_API_KEY"    # 用于双人效果（sv2）
```

> 📌 `api_key` 和 `api_key_v2` 需要自行从 [apix.iqfk.top](https://apix.iqfk.top) 获取。

## 🎮 使用

### 基本命令

```
/表情 <QQ号>                      → 随机 V1 效果
/表情 <QQ号> <效果>               → 指定 V1 效果
/表情 <QQ号1> <QQ号2>             → 随机 V2 效果
/表情 <QQ号1> <QQ号2> <效果>      → 指定 V2 效果
/表情列表                         → V1 效果图片菜单
/表情2列表                        → V2 效果图片菜单
```

### @自己

```
/表情 @我 精神小伙                → 用自己的头像生成
/表情 @自己 QQ号 击剑             → 自己 + 对方双人效果
```

### 效果指定方式

| 方式 | 示例 | 说明 |
|------|------|------|
| 序号 | `/表情 QQ 42` | 在菜单里找到效果的页码+序号 |
| 完整值 | `/表情 QQ beat_up` | 效果英文标识 |
| 完整名 | `/表情 QQ 揍` | 效果中文名称 |
| 模糊 | `/表情 QQ 学` | 匹配包含「学」的效果（如「米学长手机」）|

### 支持格式

- ✅ 纯 QQ 号：`/表情 123456789 效果`
- ✅ @自己：`/表情 @Ling 效果`
- ✅ 混合引用：`/表情 @Ling 123456789 效果`
- ✅ 无空格命令：`/表情123456789效果`

## 📋 V2 双人效果列表

| 序号 | 名称 | 说明 |
|------|------|------|
| 1 | 击剑 (fencing) | 两人持剑对决 |
| 2 | 贴贴 (tietie) | 两人贴贴 |
| 3 | 抱抱 (hug) | 两人拥抱 |
| 4 | 揍 (beat_up) | 揍对方 |
| 5 | 结婚 (married) | 结婚证书 |
| 6 | 舔 (lick) | 舔屏幕 |
| 7 | 超市 (do) | 超市捏 |
| 8 | 口 (oral_sex) | 口 |

> 完整 18 种效果请用 `/表情2列表` 查看。

## 🧩 兼容性

- **MaiBot**：`^1.0.0`
- **MaiBot SDK**：`^2.0.0`
- **平台**：QQ（通过 NapCat 适配器）
- **Python**：3.10+

## 📂 项目结构

```
ling_avatar-meme/
├── _manifest.json    # 插件清单
├── plugin.py         # 插件主文件
├── config.toml       # 配置文件
├── LICENSE           # MIT 许可证
└── README.md         # 本文档
```

## 📝 更新日志

### v3.3.0
- 🔧 修复 `@staticmethod` 导致 `@mention` 无法解析
- 🔧 严格 V1/V2 分流：1QQ → V1，2QQ → V2
- ✨ 支持 `@自己` 自动解析为发送者 QQ
- ✨ 效果列表每日自动缓存

### v3.2.0
- ✨ 新增 V2 双人效果支持（18 种）
- ✨ `/表情2列表` 查看双人效果

### v3.0.0
- 🎉 首次发布：329 种效果
- 📋 `/表情列表` 图片菜单

## 📄 许可证

MIT © Ling-LA

---

> Made with ❤️ for [MaiBot](https://github.com/Mai-with-u/MaiBot)
