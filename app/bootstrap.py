"""启动初始化：校验配置、自检关键模块可导入。

容器启动时由 entrypoint.sh 调用（python -m app.bootstrap）。
无数据库等外部依赖；这里执行运行环境自检并输出启动横幅。
"""

from __future__ import annotations

import sys


def main() -> int:
    print("[bootstrap] 小批量标签拼版工具 —— 初始化开始")

    # 依赖与核心模块自检
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
        import pydantic  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        print(f"[bootstrap] 依赖缺失: {exc}", file=sys.stderr)
        return 1

    from .layout import compute_layout
    from .models import LabelSpec, LayoutRequest, OccupiedZone
    from .svg import build_svg

    # 用一个最小样例冒烟测试排版 + SVG 管线
    smoke = LayoutRequest(
        page_width=210, page_height=297,
        margin_top=8, margin_right=8, margin_bottom=8, margin_left=8,
        gap_x=2, gap_y=2,
        labels=[LabelSpec(width=60, height=30, count=4, allow_rotate=True)],
    )
    plan = compute_layout(smoke)
    build_svg(plan, 1)
    assert plan.total_placed == 4

    # 占用区自检：首张纸障碍 + 裁切间距 + 份数不丢失
    zone = OccupiedZone(x=8, y=8, width=60, height=40)
    reused = LayoutRequest(
        page_width=210, page_height=297,
        margin_top=8, margin_right=8, margin_bottom=8, margin_left=8,
        gap_x=2, gap_y=2,
        occupied_zones=[zone],
        labels=[LabelSpec(width=60, height=30, count=30, allow_rotate=True)],
    )
    reused_plan = compute_layout(reused)
    build_svg(reused_plan, 1, show_occupied=True)
    build_svg(reused_plan, 1, show_occupied=False)
    assert reused_plan.total_placed == 30, "占用区场景下份数统计有误"
    for lab in reused_plan.pages[0].labels:
        assert (
            lab.x + lab.width <= zone.x - reused.gap_x + 1e-6
            or lab.y + lab.height <= zone.y - reused.gap_y + 1e-6
            or lab.x >= zone.x + zone.width + reused.gap_x - 1e-6
            or lab.y >= zone.y + zone.height + reused.gap_y - 1e-6
        ), "首页标签与占用区的裁切间距不足"

    # 越界占用区必须报出明确错误
    out_of_page = LayoutRequest(
        page_width=210, page_height=297,
        occupied_zones=[OccupiedZone(x=200, y=8, width=20, height=10)],
        labels=[LabelSpec(width=60, height=30, count=1)],
    )
    try:
        compute_layout(out_of_page)
    except ValueError as exc:
        assert "占用区" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("越界占用区未被拒绝")

    print(f"[bootstrap] 自检通过（FastAPI {fastapi.__version__}, "
          f"Pydantic {pydantic.VERSION}）")
    print("[bootstrap] 初始化完成，等待 uvicorn 启动 ...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
