# Agent 指令遵循改进方案

## 问题背景

在执行指令 `"打开应用宝,下载抖音,安装抖音,并且在抖音里面搜索orangepi"` 时,Agent 错误地下载了**快手**而不是**抖音**。

## 根因分析

### 核心原因
MAI-UI-8B 视觉语言模型的决策错误,可能原因包括:

1. **视觉混淆**: 应用宝搜索结果页面中,"抖音"和"快手"图标位置接近,模型误判点击坐标
2. **语义理解偏差**: 模型将"下载短视频App"作为主要目标,未严格遵循"抖音"这个具体名称
3. **Prompt 约束不足**: System Prompt 中缺少对精确名称匹配的强制要求
4. **缺少验证机制**: 在点击前没有校验当前选中的App名称是否与目标一致

### 技术层面
- 客户端代码 (`main.py`) 只负责执行模型输出的动作,**不参与决策**
- 所有决策逻辑由 VLM (Vision-Language Model) 完成
- 缺少执行日志,无法复盘模型的思考过程

## 实施的改进方案

### 1. 增强 System Prompt (Critical Rules)

**文件**: `src/prompt.py`

**改进内容**:
```python
## Critical Rules (MUST FOLLOW)
- **Exact Name Matching**: When user specifies an app name (e.g., "抖音", "微信", "TikTok"), 
  you MUST interact with EXACTLY that app. 
  - DO NOT click on similar or alternative apps
  - If exact app not visible, scroll to find it instead of clicking alternatives
  - In <thinking> tag, explicitly verify: "I can see [app_name] on screen at [location]"
  
- **Verification Before Action**: Before clicking any app icon or download button, 
  verify in your thinking process that the visible text matches the user's instruction.
  
- **Fail Gracefully**: If you cannot find the exact app after scrolling, 
  use {"action": "answer", "text": "Cannot find [app_name]"} instead of clicking wrong targets.
```

**影响**:
- ✅ 强制模型在 `<thinking>` 中明确说明看到的App名称
- ✅ 要求精确匹配,不允许点击相似应用
- ✅ 找不到目标时优雅失败,而不是误操作

### 2. 添加执行日志保存

**文件**: `main.py`

**新增功能**:
- 自动创建 `logs/session_TIMESTAMP/` 目录
- 保存每一步的:
  - 📸 截图 (`step_XXX_screenshot.png`)
  - 🧠 模型原始输出 (包含 `<thinking>` 内容)
  - 🎯 执行的动作和参数
  - 📋 任务元信息

**新增参数**:
```bash
--save-logs      # 是否保存日志 (默认: True)
--log-dir        # 日志目录 (默认: logs)
```

**日志结构**:
```
logs/
└── session_20260105_195230/
    ├── task_info.json          # 任务元信息
    ├── execution_log.json      # 完整执行日志
    ├── step_001_screenshot.png # 第1步截图
    ├── step_001_log.json       # 第1步详细日志
    └── ...
```

**影响**:
- ✅ 可复盘每次执行,查看模型的思考过程
- ✅ 定位问题时可查看当时的屏幕状态
- ✅ 收集失败案例用于模型改进

### 3. 创建日志分析工具

**文件**: `analyze_logs.py`

**功能**:
- 解析会话日志
- 提取每一步的 `<thinking>` 内容
- 生成可读的复盘报告
- 统计动作类型分布

**使用方法**:
```bash
python analyze_logs.py logs/session_20260105_195230
```

**输出示例**:
```
📊 Agent 执行复盘分析报告
================================================================================

📝 任务信息:
  时间: 20260105_195230
  指令: 打开应用宝,下载抖音,安装抖音,并且在抖音里面搜索orangepi
  设备: 10.31.0.210:10030
  模型: MAI-UI-8B
  总步数: 15

🔍 逐步执行分析:
--------------------------------------------------------------------------------

【步骤 1】
  动作类型: open
  打开应用: 应用宝
  思考过程:
    用户要求打开应用宝
    我需要使用open动作打开应用宝
    
【步骤 2】
  动作类型: type
  输入文本: 抖音
  思考过程:
    应用宝已打开
    现在需要搜索"抖音"
    我看到搜索框,点击后输入"抖音"
    
【步骤 3】
  动作类型: click
  点击坐标: [0.5, 0.3]
  思考过程:
    搜索结果已显示
    ⚠️ 我看到"快手"在坐标 [0.5, 0.3]  <-- 这里就能发现问题!
    点击下载按钮
...
```

**影响**:
- ✅ 快速定位决策错误的步骤
- ✅ 理解模型为什么做出某个决策
- ✅ 验证 Prompt 改进是否生效

### 4. 更新文档

**文件**: `README.md`

**新增章节**:
- CLI 参数表格中添加 `--save-logs` 和 `--log-dir`
- 新增 "Execution Logs and Replay Analysis" 章节
- 说明日志结构和分析方法
- 列出日志的典型用途

## 使用建议

### 下次执行时

1. **启用 Debug 模式**:
```bash
python main.py --debug \
  --device-id 10.31.0.210:10030 \
  --base-url http://10.31.0.246:8000/v1 \
  --model "MAI-UI-8B" \
  "打开应用宝,下载抖音,安装抖音,并且在抖音里面搜索orangepi"
```

2. **执行后分析日志**:
```bash
# 找到最新的会话目录
ls -lt logs/

# 分析日志
python analyze_logs.py logs/session_XXXXXX_XXXXXX
```

3. **检查关键步骤的 thinking**:
   - 在搜索结果页面,模型是否明确说明看到了"抖音"?
   - 点击下载按钮前,是否验证了App名称?
   - 如果还是点错了,thinking 中的描述是什么?

### 持续改进

如果问题仍然存在,可以进一步:

1. **在 Prompt 中添加示例**:
   ```
   Example (CORRECT):
   <thinking>
   I can see "抖音" app at position [0.5, 0.4]
   I will click the download button next to "抖音"
   </thinking>
   
   Example (WRONG - DO NOT DO THIS):
   <thinking>
   I see a short video app, I will click it
   </thinking>
   ```

2. **添加视觉校验层**:
   - 在点击前,让模型先执行一个 "grounding" 任务
   - 确认目标元素的文本内容
   - 只有匹配时才执行点击

3. **收集失败案例**:
   - 将所有"点错App"的日志收集起来
   - 用于 Fine-tuning 或 RLHF 训练

## 预期效果

| 改进项 | 预期效果 |
|--------|---------|
| **Enhanced Prompt** | 模型在 thinking 中明确验证App名称,减少误点击 |
| **Execution Logs** | 100% 可复盘,快速定位问题根因 |
| **Analysis Tool** | 5分钟内完成一次执行的完整复盘 |
| **Documentation** | 团队成员都能使用日志功能进行调试 |

## 总结

这次改进从三个层面解决问题:

1. **预防** (Enhanced Prompt): 通过更严格的约束,降低模型犯错概率
2. **检测** (Execution Logs): 记录完整执行过程,快速发现问题
3. **分析** (Analysis Tool): 提供工具快速复盘,理解根因

**关键点**: 由于决策完全由 VLM 控制,我们无法从代码层面"修复"这个问题,只能通过:
- 更好的 Prompt Engineering
- 更完善的日志和分析工具
- (长期) 模型训练改进

---

**创建时间**: 2026-01-05  
**改进版本**: v1.0
