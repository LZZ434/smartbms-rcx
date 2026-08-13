# Three-minute Demo Script

## Before the interview

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\generate_portfolio.py --output generated
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Keep `generated/scenario-comparison.csv` open as arithmetic evidence. Use the default configuration; do not change parameters immediately before an interview.

## 中文三分钟讲稿

### 0:00–0:20｜先讲边界

“这是一个楼宇 HVAC 控制和再调试诊断的离线概念验证。所有天气、负荷、BMS 趋势和节能数据都是合成的，没有连接真实楼宇。我做它的目标，是把自动化专业里的建模、控制、故障诊断和上层软件串起来。”

操作：停在 **Overview**，指向黄色合成数据声明。

### 0:20–0:45｜给出问题和结果

“场景是香港两区办公室，一周、15 分钟采样。相同天气和负荷下，预测监督控制比基线少用 5.623% HVAC 能耗；峰值只降低 0.745%，我没有夸大。优化场景的占用时舒适率是 100%。四类注入故障全部在第四个连续采样点检出，也就是 45 分钟。”

操作：指出四个 KPI 卡片。

### 0:45–1:25｜解释模型和控制

“每个区用一阶 RC 热模型：围护结构传热、内部负荷、太阳得热减去供冷，得到下一时刻温度。风机用三次方律，冷机功率用供冷量除以有效 COP。基线是时序加 P 控制；预测策略不是深度学习，也不是完整 MPC，而是在一小时天气和占用预测下搜索有限目标温度，用能耗、峰值和舒适惩罚选动作，异常输入会回退到基线。”

操作：打开 **Plant & Control**，展示温度/目标、功率、命令/反馈曲线；展开公式。

### 1:25–1:55｜说明节能不能偷舒适度

“我没有只看能耗。指标直接从 15 分钟功率积分，同时计算 22 到 26 度舒适率和度时。基线早晨没有预冷，所以存在舒适缺口；预测策略提前冷却并减少非占用运行。最终能耗从 844.288 降到 796.814 kWh，舒适度时数从 6.253 降为 0。”

操作：打开 **Energy Optimization**，指向比较表和两条功率曲线。

### 1:55–2:15｜先做数据质量准入

“真实 RCx 不能拿到 CSV 就直接报故障。我先严格解析时间戳、数值和布尔字段，再检查重复/乱序/不规则采样、缺失、冻结、工程范围、温度突变和跨点位矛盾。四类规则各有自己的必要点位；数据不足时显示‘不能运行’，而不是误报成‘设备健康’。”

操作：打开 **Data Quality & Import**，指出健康样例的 100 分、八项检查和 4/4 规则准入；说明上传文件只在内存处理。

### 2:15–2:40｜做一次 RCx 诊断

“这里我选阀门卡滞。控制器给了较大供冷命令，但阀门反馈停在 0.15，持续四个采样点后形成高严重度 finding。系统不是只报一个 alarm，而是给出命令—反馈证据、影响估计和下一步动作：检查执行器连杆，再做全开全关功能测试。”

操作：打开 **RCx Diagnostics**，选择 `Stuck Valve`，指向证据、检测时刻和建议。

“另外三类是传感器偏置、过滤器堵塞和非工作时段运行。健康场景没有 RCx finding；预测预冷也被显式标为授权，避免误报。”

### 2:40–2:55｜展示 BMS 思维

“点表有 19 个模拟点，包括单位、读写属性、BACnet 对象和 Modbus 寄存器。它不是实际通讯驱动，但能说明我理解一个点如何进入趋势、报警、诊断和界面。”

操作：打开 **BMS Points & Alarms**，筛选 `AHU-1`。

### 2:55–3:00｜收尾

“项目有 99 个自动化测试和可复算 CSV，包括严格导入、质量门控、中英文七页渲染和双语报告测试。拿到真实数据后，我仍会先确认点位语义、标定和技术人员反馈，再评估有联锁的控制写入。”

## 45-second English version

“SmartBMS-RCx is a public synthetic proof of concept for building HVAC controls and retro-commissioning. It combines a two-zone RC model, bounded predictive supervision, four injected faults, strict in-memory CSV ingestion, eight data-quality checks, rule-specific diagnostic admission, and a bilingual seven-page dashboard. In the fixed scenario, simulated energy decreased from 844.288 to 796.814 kilowatt-hours—5.623%—with 100% occupied comfort, while all four injected faults were detected after 45 minutes. These are model-specific results, not real-building savings or live BACnet deployment. The repository includes 99 automated tests and reproducible interval CSVs.”

## If the interviewer interrupts

- “Is this real data?” — “No. It is deterministic synthetic data anchored to HKO summer normals. The limitation is explicit in the UI, report, and résumé wording.”
- “Is this MPC?” — “No. It borrows prediction and objective ideas but uses bounded candidate search without a formal constrained optimizer.”
- “Why is peak reduction small?” — “The objective prioritizes energy and comfort, and pre-cooling can retain a high morning peak. I report the 0.745% result rather than hiding it.”
- “Can it control BACnet?” — “No. The current version models points and alarms only. I would start a real deployment with read-only ingestion and security/data-quality gates.”
- “What did you personally learn if Codex generated it?” — Explain one experiment from the Learning Lab, one failure you debugged, and one change you can implement live.
