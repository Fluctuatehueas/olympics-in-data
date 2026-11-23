# 数说奥运 · 可交互看板

Vue 3 + Vite + Element Plus + ECharts，数据由 Python FastAPI 后端读取 `dashboard.json` 提供。

## 启动

### 1. 生成数据（只需一次）

```bash
python backend/api/build_data.py
```

脚本只依赖 Python 标准库，读取 `olympics_dataset.csv` 与 `outputs/tables/*`，输出
`backend/api/data/dashboard.json`（约 800 KB）。

### 2. 启动后端（8010）

```bash
python -m pip install -r backend/api/requirements.txt
python backend/api/main.py
```

- `GET /api/health`：健康检查
- `GET /api/dashboard`：整包数据
- `GET /api/dashboard/{section}`：按区块取数

### 3. 启动前端（8080）

```bash
cd frontend/datavision
npm install
npm run dev
```

访问 http://127.0.0.1:8080/ 。

> 原配置的 5500 落在 Windows 保留端口段（5474–5573），会导致 `EACCES`，因此改为 8080；
> `vite.config.js` 已把 `/api` 代理到 `http://127.0.0.1:8010`。

生产构建：`npm run build`，产物在 `dist/`。

## 页面

| 路由 | 页面 | 主要内容 |
|---|---|---|
| `/overview` | 全局概览 | 奖牌膨胀、总榜前 10、女性弧线、东道主增益、5 条洞察 |
| `/medals` | 奖牌格局 | 逐届构成、区间总榜、历史明细表、重点国家轨迹 |
| `/countries` | 国家兴衰 | 多国曲线、主办届标记、国家 × 届次热力、国家档案 |
| `/gender` | 她的奥运 | 女性占比弧线、女子小项供给、各国女性占比、明细表 |
| `/sports` | 项目演化 | 运动生命周期、小项数量与泛化占比、运动明细 |
| `/caliber` | 口径的魔力 | 2024 双口径对照、排名位移、放大倍数、明细表 |
| `/host` | 东道主效应 | 主办届前后对照、增益、赛后回落、明细表 |

## 联动

顶部全局状态（Pinia）包含：

- 口径：小项口径 / 运动员行口径
- 届次区间：两个下拉框，联动筛选所有图表与表格
- 当前选择：届次、国家（可多选）、运动

点击图表中的柱子 / 折线点 / 热力格 / 散点，或点击表格行，会写入同一份状态，
其它图表通过 `markLine`、颜色高亮、数据过滤同步响应。工具栏显示当前选择，
支持「清除联动」与「重置全部」。

## 样式

蓝白扁平风：顶部蓝色渐变、白色侧栏、1px 分隔线，无圆角卡片、无阴影。
Element Plus 的圆角与阴影已在 `src/style.css` 中通过 CSS 变量与选择器覆盖为 0。
