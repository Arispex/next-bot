# 优化进度页面样式

## Goal

重新设计进度功能的截图渲染页面，引入 boss 图片，打造 Terraria 风格的高质感视觉效果。

## 子任务

### 1. 统一 boss 图片文件名

当前文件名格式混乱（含尺寸前缀、括号、下划线等）：
```
123px-Skeletron_Prime.gif
150px-Twins_(first_form).gif
170px-Skeletron.webp
94px-Nebula_Pillar.webp
...
```

目标：统一为 `{apiKey}.{原扩展名}` 格式，与 `_PROGRESS_NAME_MAP` 的 key 对应：

| 原文件名 | 新文件名 |
|---------|---------|
| King_Slime.gif | kingSlime.gif |
| Eye_of_Cthulhu_(Phase_1).gif | eyeOfCthulhu.gif |
| Eater_of_Worlds.webp | eaterOfWorldsOrBrainOfCthulhu.webp |
| Brain_of_Cthulhu_(First_Phase).gif | 删除（保留 Eater 版） |
| Queen_Bee.gif | queenBee.gif |
| 170px-Skeletron.webp | skeletron.webp |
| Deerclops.png | deerclops.png |
| Wall_of_Flesh.gif | wallOfFlesh.gif |
| Queen_Slime.webp | queenSlime.webp |
| 150px-Twins_(first_form).gif | theTwins.gif |
| The_Destroyer.webp | theDestroyer.webp |
| 123px-Skeletron_Prime.gif | skeletronPrime.gif |
| Plantera_(First_form).gif | plantera.gif |
| Golem.webp | golem.webp |
| Duke_Fishron_(First_Form).gif | dukeFishron.gif |
| Empress_of_Light.gif | empressOfLight.gif |
| Lunatic_Cultist.gif | lunaticCultist.gif |
| 94px-Solar_Pillar.webp | solarPillar.webp |
| 94px-Nebula_Pillar.webp | nebulaPillar.webp |
| 94px-Vortex_Pillar.webp | vortexPillar.webp |
| 94px-Stardust_Pillar.webp | stardustPillar.webp |
| Moon_Lord.gif | moonLord.gif |

### 2. 补充 boss 图片静态路由

在 `server/routes/render.py` 添加 `/assets/imgs/boss/{filename}` 路由（仿照现有 items/dicts 路由），供 Playwright 访问。

### 3. 重设计 progress.html

风格目标：
- 暗色 Terraria 风格：深色背景、石砖/地下城质感
- 每个 boss 卡片包含图片、中文名、已击败/未击败状态
- 已击败：金色/绿色高亮，未击败：灰暗压抑
- 顶部展示服务器信息 + 进度条（X/21 已击败）
- 宽屏截图友好（viewport 1700px）

HTML 中用 JavaScript lookup table 将中文名映射到图片文件名（apiKey），图片 URL 为 `/assets/imgs/boss/{apiKey}.{ext}`。

## Acceptance Criteria

- [ ] boss 图片文件名统一为 camelCase apiKey 格式
- [ ] 添加 `/assets/imgs/boss/` 静态路由
- [ ] 进度页面显示 boss 图片
- [ ] 暗色 Terraria 主题，已击败/未击败视觉区分清晰
- [ ] 页面在 1700px 宽度下截图效果良好

## Files to Modify

- `server/assets/imgs/boss/`（重命名）
- `server/routes/render.py`（添加路由）
- `server/templates/progress.html`（完全重设计）
