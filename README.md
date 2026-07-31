# 铁板神数 · 先天考刻推演系统

铁板神数是中国古代命理预测方法之一。本项目实现了一套完整的铁板神数推演算法——先天命数、八刻定刻、本命条文、后天命数、流年推演等，并提供传统风格的 Web 界面。

**纯前端运行**：全部算法（含农历/八字换算）均在浏览器端 JavaScript 完成，无需后端，可直接部署到 Cloudflare Pages 等静态托管平台。

## 文档

- [使用手册](docs/使用手册.md) — 如何排盘、如何看懂结果
- [铁板神数方法](docs/铁板神数方法.md) — 本系统实现的算法体系
- [技术文档](docs/技术文档.md) — 架构、数据结构、移植校验与构建
- 文档目录：[docs/](docs/README.md)

## 功能

- **先天命数**：由出生年月日时自动推算
- **八刻定刻**：精确到刻（15 分钟）细分时辰，得刻干数
- **本命条文**：本命卦、命数、条文与断语
- **后天命数 / 五数寄宫**：含三元九运判定
- **八卦加则**：「遇十当不用、变知六八止」演变
- **流年推演**：1–108 岁完整流年，虚岁旁标注对应公历年
- **断语现代白话**：原条文 / 校正后 / 铁板公式三种断语均附白话释义
- **打印支持**：可生成打印版报告

铁板核心公式：`终局条文数 = 本命数 + 刻干数 × 48`。算法细节见[方法文档](docs/铁板神数方法.md)。

## 快速开始

### 部署到 Cloudflare Pages（纯前端）

打包以下文件（保持目录结构），在 Cloudflare Pages 选择「直接上传（Direct Upload）」拖入即可，无需构建命令与环境变量：

```
index.html  result.html  Print.html  favicon.svg
css/app.css
js/lunar.js  js/db-data.js  js/tieban.js  js/duanyu-modern.js  js/terms.js
```

同样适用于 GitHub Pages、Vercel、Netlify，或本地直接用浏览器打开 `index.html`。

### 可选：混淆压缩后发布

```bash
npm i terser javascript-obfuscator html-minifier-terser
node tools/build.js        # 产物在 tools/dist/
```

核心算法 `tieban.js` 与 HTML 内联脚本做混淆，`lunar.js` / `db-data.js` / `duanyu-modern.js` 做压缩。
> 纯前端代码与数据最终都在浏览器执行，混淆只提高逆向门槛，无法真正加密。

### 本地开发（Python 参照实现）

Python 版保留用于对照/调试：

```bash
pip install -r requirements.txt
python server.py          # 访问 http://127.0.0.1:8000
```

> 前端页面默认走纯前端计算，不再依赖 `/api/calculate` 后端接口。

## 项目结构

```
├── index.html            # 输入表单
├── result.html           # 结果展示（移动优先，参数可点看白话解释，流年可展开卡片）
├── Print.html            # 完整报告 / 打印版（含名词白话对照表）
├── css/app.css           # 共享设计系统（纸墨浅色风，移动优先）
├── js/                   # 纯前端运行所需（部署仅需此目录 + 上述 HTML + css/）
│   ├── lunar.js          # 农历/八字换算库（lunar-javascript）
│   ├── db-data.js        # 由 DB/*.csv 导出的数据（window.TIEBAN_DB）
│   ├── tieban.js         # 核心算法（由 main.py 移植）
│   ├── duanyu-modern.js  # 断语现代白话对照（10719 条）
│   └── terms.js          # 排盘术语白话解释字典（window.TIEBAN_TERMS）
├── tools/build.js        # 发布构建：混淆 + 压缩
├── docs/                 # 项目文档
│
│   # 以下为 Python 参照实现，纯前端部署不需要
├── main.py               # 核心算法（参照实现）
├── server.py             # 本地 HTTP 服务器
├── requirements.txt
└── DB/                   # 数据源 CSV（已导出到 js/db-data.js）
```

## 技术栈

- **前端（生产）**：原生 HTML + CSS + JavaScript，纯浏览器端运行
- **历法**：[lunar-javascript](https://github.com/6tail/lunar-javascript)
- **数据**：`DB/*.csv` 预导出为 `js/db-data.js`
- **参照实现**：Python + http.server + cnlunar + pandas

JS 输出经逐项校验与 Python 参照实现一致（八字换算 1300+ 例、完整排盘结果 170+ 例）。

## 更新日志

### v4.0
- 界面**彻底重设计**为浅色「纸墨」现代 App 风（暖纸底 + 白卡片 + 朱砂点缀，系统字体），解决深色主题与移动端原生控件冲突、衬线字体安卓回退发虚等问题
- 结果页新交互：吸顶锚点导航、本命卦 Hero 概览、流年「三种条文怎么看」引导
- **基础排盘所有参数可点击查看白话解释**（新增 `js/terms.js` 术语字典，20 词条）；完整报告页每参数附白话微注 + 名词白话对照表

### v3.2
- 前端整体重设计为**移动优先的现代国风**（深墨底 + 酱金，大字号、大触控区、卡片化）
- 新增共享设计系统 `css/app.css`
- 流年改为**可展开卡片**（解决旧版 15 列宽表在手机上难用的问题），点开看三种条文/白话/八卦加则
- 首页改用原生日期时间选择器，提升移动端输入体验

### v3.1
- 流年表在虚岁旁增加对应公历年份
- 新增断语现代白话对照（10719 条离线预生成）
- 新增发布构建 `tools/build.js`（混淆 + 压缩）
- 新增项目文档集 `docs/`

### v3.0
- 纯前端迁移：算法与农历/八字换算移植为浏览器端 JavaScript，去除后端依赖
- 支持一键部署到 Cloudflare Pages 等静态托管

### v2.0
- 新增六亲考刻与刻别验证；完善本命条文；优化打印

### v1.0
- 初始版本：基本铁板神数算法、八刻细分、核心公式、Web 界面

## 免责声明

本系统仅供传统文化研习与娱乐，不构成任何决策依据。

## 许可证

本项目仅供学习交流使用。
