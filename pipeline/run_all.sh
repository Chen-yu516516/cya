#!/bin/bash
# =============================================================================
# Week 3 Pipeline 统一运行入口
# 从 raw → parsed → validated → reviewed 四阶段一键复现
# =============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEEK3_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STAGES_DIR="$SCRIPT_DIR/stages"

echo "========================================="
echo " Week 3 Pipeline — 统一运行"
echo " 执行路径: $WEEK3_DIR"
echo "========================================="

# ── 阶段 1: raw → auto_output ──
echo ""
echo "[阶段 1/4] 运行 week3_pipeline.py (raw → auto_output)"
cd "$SCRIPT_DIR"
python3 week3_pipeline.py

# ── 阶段 2: raw → parsed ──
echo ""
echo "[阶段 2/4] 运行 migrate_stages.py (raw → parsed)"
cd "$STAGES_DIR"
python3 migrate_stages.py

# ── 阶段 3: parsed → validated ──
echo ""
echo "[阶段 3/4] 运行 cross-check (per_event + per_shareholder)"
cd "$WEEK3_DIR/validation/cross_check"
python3 per_event_check.py
python3 per_shareholder_check.py

# ── 阶段 4: validated → reviewed ──
echo ""
echo "[阶段 4/4] reviewed 阶段需要人工对照 PDF 逐条核实"
echo "  → 已生成 reviewed Excel 位于 $STAGES_DIR/reviewed/"
echo "  → 如需修改，请对照 PDF 逐条填写 original_value/revised_value/reason/pdf_page"

echo ""
echo "========================================="
echo " Pipeline 全流程执行完毕"
echo " 产出物:"
echo "   raw:       $STAGES_DIR/raw/"
echo "   parsed:    $STAGES_DIR/parsed/"
echo "   validated: $STAGES_DIR/validated/"
echo "   reviewed:  $STAGES_DIR/reviewed/"
echo "========================================="
