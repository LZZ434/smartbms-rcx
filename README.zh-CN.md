# SmartBMS-RCx：楼宇 HVAC、BMS 与再调试作品集

[![CI](https://github.com/LZZ434/smartbms-rcx/actions/workflows/ci.yml/badge.svg)](https://github.com/LZZ434/smartbms-rcx/actions/workflows/ci.yml)
[![在线演示](https://img.shields.io/badge/在线演示-Streamlit-ff4b4b)](https://smartbms-rcx-hk.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

这是一个可解释、可离线运行的工程概念验证项目，覆盖楼宇空调控制、能耗优化、BMS 点表/报警语义，以及再调试（RCx）故障诊断。

> **必须先讲清楚的边界：** 项目中的天气、人员、负荷、BMS 趋势、故障、费用和节能结果全部是合成数据。它没有连接真实办公楼，没有实现真实 BACnet/Modbus 通讯，也不能保证实际项目获得相同节能率。

[English README](README.md)

**[打开公开中英双语仪表盘](https://smartbms-rcx-hk.streamlit.app)** · [查看源代码](https://github.com/LZZ434/smartbms-rcx)

免费 Community Cloud 在连续约 12 小时无人访问后可能休眠；看到休眠页时点击唤醒，稍等片刻即可。

![RCx 仪表盘](docs/assets/rcx-dashboard.png)

## 已验证的合成场景结果

默认场景固定为：香港两区办公室、7 天、15 分钟采样、随机种子 `20260803`。

| 指标 | 基线控制 | 预测监督控制 | 变化 |
|---|---:|---:|---:|
| HVAC 能耗 | 844.288 kWh | 796.814 kWh | 降低 5.623% |
| 峰值功率 | 18.646 kW | 18.507 kW | 降低 0.745% |
| 占用时 22–26 °C 舒适率 | 86.889% | 100.000% | 提高 13.111 个百分点 |
| 占用时不舒适度 | 6.253 °C·h | 0.000 °C·h | 降低 6.253 °C·h |
| 大于 0.5 kW 的运行时长 | 83.50 h | 69.25 h | 减少 14.25 h |
| 示例周费用 | HK$1,922.92 | HK$1,852.99 | 降低 3.637% |

四类注入故障——温度传感器偏置、阀门卡滞、过滤器堵塞、非工作时段运行——在固定测试场景中全部检出：**召回率 4/4、检测延迟 45 分钟、额外误报 0 项**。

这些数值由 15 分钟趋势自动计算，并由 `tests/test_scenarios.py` 验证；仪表盘没有另写一套“好看数字”。

## 这个项目能证明什么

- 你能解释两区一阶 RC 热模型、内扰和东西向太阳得热，而不只会调用现成库。
- 你能区分时序/P 控制基线与带一小时预测的有界候选搜索，并说明安全回退。
- 你理解冷机 COP、风机三次方律和 kW/kWh/°C·h 等工程单位。
- 你能把故障注入、趋势证据、持续性判断、严重度、影响估计和维修建议串成 RCx 闭环。
- 你能设计 19 个模拟 BMS 点位的 BACnet 对象、Modbus 寄存器和报警语义。
- 你能对上传 CSV 做严格类型解析、八项确定性质量检查和按规则准入，避免把“数据不足”误报成“设备健康”。
- 你能运行默认中文、可切换 English 的七页 Streamlit 仪表盘，并导出跟随当前语言的 HTML/Markdown 报告、原始 CSV 和清单文件。

它不能证明你做过真实现场调试、BACnet 联调或实际节能量测。面试时主动说清边界，反而更专业。

## Windows 一键运行

### 60 秒在线体验

1. 打开[在线应用](https://smartbms-rcx-hk.streamlit.app)，先看合成数据边界。
2. 打开“数据质量与导入”，查看健康样例的八项检查和四类规则准入。
3. 下载标准样例并重新上传，再进入“再调试（RCx）诊断”查看证据如何对应现场动作。

上传文件最大 10 MB，只在当前 Streamlit 进程/会话的内存中处理，本应用不会保存。使用其他字段前请阅读[趋势数据契约](docs/data-contract.md)。

建议使用 Python 3.11 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

浏览器未自动打开时访问 `http://localhost:8501`。

仪表盘默认显示中文。使用侧边栏顶部的 `语言 / Language` 可切换整个界面；HTML 和 Markdown 下载文件会分别使用 `-zh` 或 `-en` 文件名。为便于 Python、Excel 和真实 BMS 数据对接，原始 CSV 字段名保持英文。

生成报告和全部 CSV：

```powershell
.\.venv\Scripts\python.exe scripts\generate_portfolio.py --output generated
```

## 面试演示顺序

1. 在 Overview 先说“合成数据概念验证”，展示 5.623% 与 4/4，但立刻说明仅适用于固定场景。
2. 在 Plant & Control 解释 RC 方程、风机三次方律、基线与预测控制的差别。
3. 在 Energy Optimization 用同一天气/负荷对比能耗、峰值和舒适度，说明不能牺牲舒适度换节能。
4. 在 Data Quality & Import 说明数据为什么必须先过质量门槛，以及不同规则为何需要不同点位。
5. 在 RCx Diagnostics 任选一类故障，从趋势证据推到维修动作。
6. 在 BMS Points & Alarms 解释点表、对象类型、寄存器、只读/可写和报警优先级。
7. 最后打开 Learning Lab，说明你如何把 Codex 生成的项目变成自己能独立修改的项目。

完整三分钟讲稿见 [demo-script.md](docs/demo-script.md)。

## 代码结构

```text
smartbms/config.py       参数与校验
smartbms/weather.py      香港夏季合成天气/占用/负荷
smartbms/plant.py        两区热模型和 HVAC 功率
smartbms/controllers.py  基线与预测监督控制
smartbms/faults.py       四类故障注入
smartbms/points.py       BMS 点表和报警
smartbms/diagnostics.py  RCx 持续性诊断
smartbms/trend_io.py     严格内存 CSV 与类型边界
smartbms/data_quality.py 八项检查与规则准入
smartbms/screening.py    质量门控的只读 RCx 筛查
smartbms/metrics.py      能耗/峰值/舒适度/费用
smartbms/scenarios.py    全场景编排
smartbms/i18n.py         中英文界面与工程展示翻译
smartbms/reporting.py    报告与 CSV 导出
app.py                   七页中英双语 Streamlit 前端
tests/                   101 个自动化测试
```

## 结果复算

在简历写任何数字前，必须重新运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\generate_portfolio.py --output generated
```

然后检查：

- `generated/scenario-comparison.csv`：能耗、峰值、舒适度和费用；
- `generated/diagnostic-scorecard.csv`：故障召回率和延迟；
- `generated/diagnostic-findings.csv`：证据与建议；
- `generated/trends-*.csv`：逐点复算；
- `generated/manifest.json`：数据分类和文件清单。

## 重要局限

- 热模型没有用真实楼宇数据标定。
- “预测控制”是有界候选搜索，不是深度学习，也不是完整 MPC 求解器。
- 传感器偏置诊断使用仿真参考温度；真实项目需用标定模型、冗余传感器或便携仪表。
- 故障影响是场景估计，不是正式 M&V 节能量。
- BACnet/Modbus 仅为点表语义，不含网络发现、写入联锁、网络安全或现场投运。
- 示例费率不是当前电力公司报价。
- 上传 CSV 只做只读筛查；规则可运行不等于传感器已校准、技术人员已确认或方案获准部署。
- 公开应用不保存上传文件，也没有 BACnet/Modbus/MQTT 连接或控制写入路径。

建议按 [三周学习计划](docs/learning-plan.md)逐步接管代码；准备投递前使用 [真实简历表述](docs/resume-bullets.md)和 [面试问答](docs/interview-guide.md)。

## 数据与方法参考

- [香港天文台 1991–2020 年 8 月常值](https://www.hko.gov.hk/en/cis/normal/1991_2020/dnormal08.htm)：只用于锚定合成夏季曲线。
- [机电工程署再调试技术指引](https://www.emsd.gov.hk/filemanager/en/content_718/Technical_Guidelines_Retro-commissioning.pdf)：用于 RCx 流程背景。

5.623% 节能结果不是来源网站给出的，而是本仓库公开模型在固定合成场景中的计算结果。
