# License decision / App 仓库许可证决策指南

MyVoiceTyping 的 App 仓库已选择 [MIT License](../LICENSE)。这个决定解决了早期推广中最容易劝退用户和收录渠道的许可证不确定性：

- 周刊 / 产品目录 / awesome list 是否愿意收录；
- 开发者是否敢于 fork、二次开发或贡献 PR；
- 企业用户是否敢于试用、评估或内部推荐；
- GitHub 页面是否显示清晰的 License badge；
- “开源、本地优先、0 费用”这个卖点是否足够可信。

> 这份文档不是法律意见。它只是帮助项目维护者快速选择一个与增长目标、开源协作和数据/模型边界相匹配的许可证。最终选择应由项目维护者确认。

## 先区分三个资产

MyVoiceTyping 不是单一资产，而是三部分：

| 资产 | 当前位置 | 建议单独看待 |
|---|---|---|
| App 代码 | <https://github.com/botaruibo/MyVoiceTyping> | 已使用 MIT License |
| 文本润写模型 | <https://modelscope.cn/models/botaruibo/MyVoiceTyping-1.5b-q4> | 当前模型页标注 Apache-2.0，但仍需遵守上游 Qwen / 量化 / 推理组件许可 |
| 调优数据集 | <https://github.com/botaruibo/MyVoiceTyping-Dataset> | 需要遵守 Dataset 的 `DATA_LICENSE`、`SOURCES` 和各原始数据源许可 |

因此 App 仓库使用 MIT，并不代表模型和数据集自动获得同样授权。README / Release / Press kit 里应继续保留这个边界。

## 面向 1000 star 的默认建议

如果当前目标是让更多人放心 Star、试用、fork、投稿周刊和收录目录，建议优先考虑：

1. **MIT**
2. **Apache-2.0**

这两类宽松许可证最适合早期开源工具增长：

- GitHub / 周刊 / awesome list 读者熟悉；
- 商业和个人使用阻力低；
- fork、二开、PR 的心理成本低；
- 不会把“能不能用”变成第一道门槛。

如果你没有强专利授权诉求，且希望最简单、最容易被理解，选 MIT 通常最省心。

如果你希望明确提供专利授权和贡献者专利保护，选 Apache-2.0 更稳健，但文本更长、理解成本略高。

## 常见选项对比

| 许可证 | 适合情况 | 优点 | 可能代价 |
|---|---|---|---|
| MIT | 希望最大化传播、Star、fork、二开和社区采用 | 简单、短、大家熟悉、阻力低 | 没有 Apache-2.0 那样明确的专利授权条款 |
| Apache-2.0 | 希望宽松开源，同时明确专利授权 | 企业接受度高、专利条款清楚、适合 AI / 工具链项目 | 文本更长，普通用户理解成本略高 |
| GPL-3.0 | 希望衍生代码也保持开源 | 强 copyleft，保护自由软件传播 | 可能降低商业/企业采用和部分周刊/目录转化 |
| AGPL-3.0 | 希望网络服务改造也必须开源 | 对 SaaS 闭源再包装约束更强 | 对工具类项目增长阻力最大，很多企业会直接避开 |
| No license | 暂时不授权别人使用 / 修改 / 分发 | 保守 | 几乎会阻塞开源协作、收录、fork 和企业试用 |

## 推荐决策路径

### 如果你最看重传播和 1000 star

推荐：

```text
MIT
```

适合文案：

```text
App code is licensed under MIT. The local polishing model and dataset have their own license / usage boundaries; please check the linked model and dataset pages before redistribution or commercial training.
```

中文说明：

```text
App 代码使用 MIT 许可证；文本润写模型和数据集有各自的许可证 / 使用边界，使用、再分发或商业训练前请查看对应模型页和数据集说明。
```

### 如果你更看重企业和专利边界

推荐：

```text
Apache-2.0
```

适合文案：

```text
App code is licensed under Apache-2.0. The local polishing model and dataset are separate assets with their own license / usage boundaries.
```

### 如果你希望强制衍生项目继续开源

可考虑：

```text
GPL-3.0
```

但这会提高企业采用、产品目录收录和二次开发的门槛。对于当前“先把早期项目推到 1000 star”的目标，不是最优先选项。

### 如果你担心别人直接包装成 SaaS

可考虑：

```text
AGPL-3.0
```

但 MyVoiceTyping 当前主要是 macOS 本地输入工具，而不是 Web 服务框架。AGPL-3.0 会显著增加采用阻力，除非你的核心目标就是强 copyleft，而不是增长。

## 选定后需要同步的地方

选定 App repo license 后，建议一次性完成：

1. 在仓库根目录新增 `LICENSE`；
2. README 顶部增加 license badge；
3. README 的 `License / 使用边界` 改成明确许可证；
4. `docs/INDEX.zh-CN.md` 删除“license 未确认”的阻塞说明；
5. `docs/PRESS_KIT.md` 更新当前状态；
6. `docs/COMMUNITY_PROOF.md` 更新 HelloGitHub / 阮一峰周刊 / awesome list 的阻塞状态；
7. Release notes 增加许可证说明；
8. Issue #7 更新或关闭；
9. 回投已提交过的周刊 / 产品目录 / awesome list。

## 建议 issue 回复模板

如果你已经决定使用 MIT：

```text
决定：App 仓库代码使用 MIT License。

原因：
- 当前目标是降低试用、fork、PR、周刊收录和产品目录收录门槛；
- MyVoiceTyping 是早期开源工具，宽松许可证更有利于获得真实用户反馈；
- 模型和数据集会继续保留独立的许可证 / 使用边界说明。

后续动作：
- 新增根目录 LICENSE；
- README / Release / Press kit / Community proof / llms.txt 同步更新；
- 保留模型和数据集的独立使用边界链接。
```

如果你决定使用 Apache-2.0：

```text
决定：App 仓库代码使用 Apache-2.0 License。

原因：
- 继续保持宽松开源，便于试用、fork 和商业评估；
- 相比 MIT，Apache-2.0 对专利授权和贡献者边界说明更明确；
- 模型和数据集会继续保留独立的许可证 / 使用边界说明。

后续动作：
- 新增根目录 LICENSE；
- README / Release / Press kit / Community proof / llms.txt 同步更新；
- 保留模型和数据集的独立使用边界链接。
```

## 当前推荐

如果没有额外法律或商业限制，且当前目标是 **1000 GitHub stars / 更多真实试用 / 更多社区收录**，推荐优先选择：

```text
MIT
```

备选：

```text
Apache-2.0
```

不要继续长期保持 `No license`。对开源增长来说，`No license` 很容易让愿意 Star / fork / 推荐的人卡在第一步。
