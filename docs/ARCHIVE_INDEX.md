# 仓库归档索引

本文档记录“已归档、不参与当前核心运行链路”的文件位置，便于后续排查或回滚。

## 一、脚本与调试文件

- `debug_eastmoney.py` -> `archive/debug/debug_eastmoney.py`
- `debug_yfinance.py` -> `archive/debug/debug_yfinance.py`
- `scripts/debug_admin_data.py` -> `archive/scripts/debug_admin_data.py`

## 二、产物与历史备份

- `poc_analysis_v1_output.json` -> `archive/artifacts/poc_analysis_v1_output.json`
- `frontend/src/components/MyJudgments.vue.backup` -> `archive/frontend/MyJudgments.vue.backup`

## 三、历史计划文档

- 索引入口：`docs/plans/README.md`

## 四、归档使用原则

- 归档文件默认不参与运行时导入和构建流程。
- 若出现历史行为回溯需求，可按原路径“回迁”文件再复测。
- 回迁后请执行最小冒烟验证，确认未引入副作用。
