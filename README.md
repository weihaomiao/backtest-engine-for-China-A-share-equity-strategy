# 日频股票回测框架

基于日频行情与策略组合的 A 股回测引擎，支持多策略配置、交易费用/负债成本、涨跌停与停牌约束，以及相对中证 500 的绩效分析。

---

## 策略回测结果
<img width="4463" height="2364" alt="全A_10个行业_equity_curve" src="https://github.com/user-attachments/assets/73eb4ab7-182c-4d08-9baa-350607419b5c" />
---


## 功能概览

- **日频回测**：按日执行调仓，支持实盘约束（涨跌停、停牌、ST/退市过滤）
- **费用与负债**：可配置买卖佣金/印花税、负债成本（`config/stock_trade_fees.json`、`config/liability_fee.json`）
- **多数据源**：QMT（股票池、全 A 日线、指数）、Wind/Choice（涨跌停、停牌）、Tushare（ST/退市补全）
- **绩效矩阵**：年化收益、夏普、最大回撤、Calmar、Sortino、相对中证 500 的 alpha/beta、跟踪误差、信息比等
- **配置驱动**：策略与路径统一在 `config/paths.yaml` 中配置，便于切换年份与策略

---

## 项目结构

```
├── run.py              # 全流程：数据更新(2–6) + 回测(7)，首次或需要更新数据时用
├── backtest.py         # 仅回测：跳过数据采集，仅跑策略数据 + main.py，多次回测时用
├── main.py             # 回测入口：读 paths.yaml，跑引擎 + 诊断 + 净值图 + 绩效
├── config/
│   ├── paths.yaml      # 数据路径、策略名/年份、输出文件名
│   ├── stock_trade_fees.json
│   └── liability_fee.json
├── backtest/           # 回测引擎（账户、持仓、调仓逻辑）
├── account/            # 资金账户、负债管理
├── trading/            # 策略相关：仓位管理、买卖逻辑（如 中证500指增_LGBM）
├── analysis/           # 诊断、净值图、绩效矩阵
├── data_collection/    # 数据采集脚本
│   ├── QMT/            # index.py, daily_data_collection.py
│   ├── wind_choice/    # 中证500指增_LGBM 周频→日频、涨跌停/停牌
│   └── tushare/        # QMT_st_fill.py（ST/退市）
├── data/               # 本地数据（不提交 Git），需自备
│   ├── level1/daily/   # 股票池、日线、指数
│   └── portfolio/      # 策略产出（如 daily_*_停牌.xlsx）
└── utils/              # 策略相关工具（如费用、指数加载）
```

---

## 环境与依赖

- Python 3.x
- 数据与运行依赖：**QMT、Wind、Choice** 需在运行数据采集步骤时已打开
- 主要库：`pandas`、`openpyxl`、`pyyaml` 等

---

## 数据准备（Step 1，手动）

1. 将**日频股票池**更新到：`data/level1/daily/stock/daily_stockpool.xlsx`
2. 若需更换回测策略或年份，在 `config/paths.yaml` 中修改对应 `input.<策略>.name` 与 `input.<策略>.year`

数据目录 `data/` 不在仓库中，需自行准备或从自有数据源生成。

---

## 运行方式

### 方式一：全流程（数据更新 + 回测）

在**项目根目录**执行，且 **QMT、Wind、Choice 已打开**：

```bash
python run.py
```

顺序执行：更新中证 500 指数 → 全 A 日线 → ST/退市补全 → 策略周频→日频 → 涨跌停/停牌 → `main.py` 回测。

### 方式二：仅回测（数据已就绪，多次回测）

数据与策略 Excel 已更新好时，只需跑回测：

```bash
python backtest.py
```

仅执行：策略相关数据脚本（如 LGBM 的 weekly_to_daily、upperlimit）+ `main.py`。

若切换策略或年份，先改 `config/paths.yaml` 再运行 `backtest.py`。

---

## 配置说明

- **`config/paths.yaml`**
  - `level1`：股票池、日线、指数所在目录
  - `input.<策略>`：策略名称 `name`、年份 `year`、组合 Excel 所在 `base_dir` 等
  - `output.<策略>`：诊断日志、日明细 CSV、绩效摘要、净值图文件名
  - `config`：交易费用、负债费用 JSON 路径

- **策略相关**  
  当前示例为 **中证500指增_LGBM**（Wind/Choice 数据用于涨跌停、停牌）。其他策略（如 中证500指增_AI团队、启航一号）可在同框架下扩展数据采集与 `paths.yaml` 配置。

---

## 输出结果

回测完成后，在对应策略的 `base_dir/year/` 下生成：

- `{name}_diagnostic_summary.txt`：每日买卖、排除原因等诊断
- `{name}_diagnostic_details.csv`：按日明细
- `{name}_performance_summary.txt`：绩效矩阵（含相对 000905.SH 的 alpha、beta 等）
- `{name}_equity_curve.png`：净值曲线图

---

## 说明

- 本框架为**日频**回测；未使用分钟数据，不做日内回测。
- 数据与本地路径需自行准备；仓库中不包含 `data/`，仅提供代码与配置示例。
