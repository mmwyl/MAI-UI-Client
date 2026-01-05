# 快速参考：如何使用新的日志和分析功能

## 🚀 快速开始

### 1. 执行任务（自动保存日志）

```bash
# 基础用法 - 日志默认开启
python main.py \
  --device-id 10.31.0.210:10030 \
  --base-url http://10.31.0.246:8000/v1 \
  --model "MAI-UI-8B" \
  "打开应用宝,下载抖音,安装抖音,并且在抖音里面搜索orangepi"

# 输出会显示日志保存位置:
# 📂 Logs will be saved to: logs/session_20260105_195230
```

### 2. 分析执行日志

```bash
# 使用分析工具
python analyze_logs.py logs/session_20260105_195230
```

### 3. 查看特定步骤的详情

```bash
# 查看某一步的完整日志
cat logs/session_20260105_195230/step_003_log.json

# 查看截图
# 使用图片查看器打开: logs/session_20260105_195230/step_003_screenshot.png
```

## 📋 日志内容说明

### task_info.json
```json
{
  "timestamp": "20260105_195230",
  "instruction": "打开应用宝,下载抖音...",
  "device_id": "10.31.0.210:10030",
  "model": "MAI-UI-8B",
  "base_url": "http://10.31.0.246:8000/v1",
  "max_steps": 50
}
```

### step_XXX_log.json
```json
{
  "step": 3,
  "action": {
    "action": "click",
    "coordinate": [0.5, 0.3]
  },
  "raw_prediction": "<thinking>\n搜索结果已显示\n我看到\"抖音\"在坐标...\n</thinking>\n<tool_call>...</tool_call>",
  "screenshot_file": "step_003_screenshot.png"
}
```

## 🔍 复盘"下载快手而不是抖音"的问题

### 步骤1: 找到相关步骤

运行分析工具后,查看输出中的 "type" 和 "click" 动作:

```
【步骤 2】
  动作类型: type
  输入文本: 抖音
  思考过程: 在搜索框输入"抖音"

【步骤 3】
  动作类型: click
  点击坐标: [0.5, 0.3]
  思考过程: 
    ⚠️ 关键: 这里查看模型说它看到了什么!
```

### 步骤2: 检查 thinking 内容

如果模型的 thinking 是:
```
<thinking>
我看到搜索结果中有一个短视频应用
我将点击下载按钮
</thinking>
```

**问题**: 模型没有明确验证App名称!

如果改进后的 thinking 是:
```
<thinking>
我看到搜索结果中有"抖音"和"快手"两个应用
用户要求的是"抖音",我将点击"抖音"的下载按钮
我确认当前选中的是"抖音"
</thinking>
```

**正确**: 模型明确验证了App名称

### 步骤3: 查看截图确认

打开对应步骤的截图:
```bash
# Windows
start logs/session_XXXXX/step_003_screenshot.png

# 或者在文件管理器中打开
explorer logs\session_XXXXX
```

对比截图和模型的 thinking,判断:
- 模型是否正确识别了屏幕上的文字?
- 点击坐标是否对应正确的App?

## 🛠️ 高级用法

### 禁用日志保存

```bash
python main.py \
  --device-id XXXXX \
  --save-logs false \
  "your instruction"
```

### 自定义日志目录

```bash
python main.py \
  --device-id XXXXX \
  --log-dir my_custom_logs \
  "your instruction"
```

### 启用 Debug 模式（更详细的输出）

```bash
python main.py \
  --debug \
  --device-id XXXXX \
  "your instruction"
```

## 📊 批量分析多个会话

```bash
# 列出所有会话
ls -lt logs/

# 批量分析（示例脚本）
for session in logs/session_*/; do
    echo "=== Analyzing $session ==="
    python analyze_logs.py "$session"
    echo ""
done
```

## ⚠️ 注意事项

1. **日志文件可能很大**: 每个截图约 100-500KB,50步任务约 5-25MB
2. **定期清理**: 建议定期清理旧的日志文件
3. **隐私**: 截图可能包含敏感信息,注意保护

## 🎯 典型问题排查流程

```
1. 执行任务 → 发现问题
   ↓
2. 运行 analyze_logs.py → 查看完整执行流程
   ↓
3. 定位问题步骤 → 查看该步骤的 thinking
   ↓
4. 打开对应截图 → 对比模型理解和实际屏幕
   ↓
5. 分析根因:
   - 模型识别错误? → 可能需要更好的截图或模型改进
   - 模型理解错误? → 需要改进 Prompt
   - 模型决策错误? → 需要添加约束或示例
```

---

**提示**: 将此文件保存为书签,方便随时查阅!
