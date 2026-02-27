import platform
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import numpy as np

# 中文与负号显示（按系统选用可用字体）
_sys = platform.system()
if _sys == "Windows":
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
elif _sys == "Darwin":
    matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti"]
else:
    matplotlib.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "Droid Sans Fallback"]
matplotlib.rcParams["axes.unicode_minus"] = False


def plot_equity_curve(
    equity_history: dict,
    benchmark: dict = None,
    title: str = "Quantitative Backtest Analysis",
    save_path=None,
):
    if not equity_history: return

    # --- 1. 数据准备 (Data Prep) ---
    s = pd.Series(equity_history).sort_index()
    s.index = pd.to_datetime(s.index, format="%Y%m%d")
    s_norm = s / s.iloc[0]

    fig, ax1 = plt.subplots(figsize=(15, 8))
    
    # 策略线 (红色 + 浅红色阴影)
    ax1.plot(s_norm.index, s_norm.values, label="Strategy", color="#e31a1c", linewidth=2.5, zorder=4)
    ax1.fill_between(s_norm.index, 1.0, s_norm.values, color="#e31a1c", alpha=0.08, zorder=3)
    
    if benchmark:
        b = pd.Series(benchmark).sort_index()
        b.index = pd.to_datetime(b.index, format="%Y%m%d")
        common = s_norm.index.intersection(b.index)
        
        if len(common) > 0:
            b_norm = b.loc[common] / b.loc[common].iloc[0]
            alpha = (s_norm.loc[common] - b_norm)
            
            # 基准线 (蓝色实线)
            ax1.plot(b_norm.index, b_norm.values, label="Benchmark", color="#1f78b4", linewidth=1.5, zorder=2)
            
            # --- 2. 右轴 Alpha 逻辑 (Secondary Axis) ---
            ax2 = ax1.twinx()
            ax2.plot(alpha.index, alpha.values, color="#d4af37", linewidth=1.8, label="Alpha (Excess)", zorder=5)
            
            # --- 3. 核心：Y轴非对称对齐算法 (Alignment Logic) ---
            # 目标：让左轴的 1.0 和右轴的 0 始终在同一水平线上，且下方留白最优化
            
            # 计算左轴需要的上下空间
            s_all = pd.concat([s_norm, b_norm])
            s_up = max(s_all.max() - 1.0, 0.05)   # 向上最小留 0.05 空间
            s_down = max(1.0 - s_all.min(), 0.05) # 向下最小留 0.05 空间
            
            # 计算右轴需要的上下空间
            a_up = max(alpha.max(), 0.01)
            a_down = max(abs(alpha.min()), 0.01)
            
            # 统一上下扩展比例 (取两轴中更极端的情况)
            # 我们要确保 P = up / (up + down) 在两边一致
            # 计算一个全局的“向上幅度”和“向下幅度”系数
            total_up = max(s_up, a_up * (s_up/a_up if a_up != 0 else 1)) * 1.15
            total_down = max(s_down, a_down * (s_down/a_down if a_down != 0 else 1)) * 1.15
            
            # 设置左轴范围
            ax1.set_ylim(1.0 - total_down, 1.0 + total_up)
            
            # 设置右轴范围，使其 0 对齐左轴 1.0
            # 比例公式：(ax2_max / total_up) = (ax2_min / total_down)
            # 简单做法：直接根据 ax1 的 limit 比例缩放 ax2
            ratio = max(a_up/s_up if s_up!=0 else 1, a_down/s_down if s_down!=0 else 1)
            ax2.set_ylim(-total_down * ratio, total_up * ratio)
            
            # 装饰右轴
            ax2.set_ylabel("Cumulative Alpha (Spread)", color="#d4af37", fontweight='bold')
            ax2.tick_params(axis='y', labelcolor="#d4af37")
            ax2.grid(False) # 右轴不重复画网格

    # --- 4. X轴日期防冲突逻辑 (X-axis Anti-Collision) ---
    start_dt = s_norm.index[0]
    end_dt = s_norm.index[-1]
    ax1.set_xlim(start_dt, end_dt)
    
    # 候选刻度：每月1号
    month_ticks = pd.date_range(start=start_dt, end=end_dt, freq='MS').tolist()
    
    # 过滤：离首尾日期太近(15天内)的刻度删掉
    final_ticks = [start_dt]
    for mt in month_ticks:
        if (mt - start_dt).days > 15 and (end_dt - mt).days > 15:
            final_ticks.append(mt)
    final_ticks.append(end_dt)
    
    ax1.set_xticks(final_ticks)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right', fontsize=10)

    # --- 5. 样式细节 (Aesthetics) ---
    ax1.set_title(title, fontsize=18, fontweight='bold', pad=25)
    ax1.set_ylabel("Normalized NAV (Base 1.0)", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.3, zorder=1)
    ax1.axhline(1.0, color="black", lw=1.2, alpha=0.5, zorder=1) # 1.0 基准线
    
    # 合并图例 (Merge Legends)
    lines1, labels1 = ax1.get_legend_handles_labels()
    try:
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", 
                   bbox_to_anchor=(0.01, 0.99), frameon=True, fontsize=10).set_zorder(10)
    except:
        ax1.legend(loc="upper left")

    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {save_path}")

    # plt.show()


