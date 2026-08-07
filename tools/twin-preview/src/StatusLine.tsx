import type { ChecklistResult } from "./checklist/runChecklist";

// One unobtrusive corner line — deliberately not a panel. See
// TWIN_PREVIEW_TOOL_PLAN.md §3.2: this tool should read as "the twin,
// rendered, movable by keyboard — nothing else."
export function StatusLine({
  assetName,
  loading,
  error,
  checklist,
}: {
  assetName: string;
  loading: boolean;
  error: string | null;
  checklist: ChecklistResult | null;
}) {
  let text: string;
  let color: string;

  if (error) {
    text = `${assetName} · ✗ ${error}`;
    color = "#ef4444";
  } else if (loading) {
    text = `${assetName} · loading…`;
    color = "#9ca3af";
  } else if (checklist) {
    const icon = checklist.ok ? "✓" : "✗";
    text = `${assetName} · ${icon} ${checklist.boundJointCount}/${checklist.jointCount} joints ok`;
    color = checklist.ok ? "#10b981" : "#ef4444";
  } else {
    text = assetName;
    color = "#9ca3af";
  }

  return (
    <div
      style={{
        position: "fixed",
        bottom: 12,
        left: 12,
        fontFamily:
          'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
        fontSize: 12,
        color,
        background: "rgba(5,7,9,0.7)",
        padding: "4px 10px",
        borderRadius: 4,
        pointerEvents: "none",
        userSelect: "none",
        zIndex: 10,
      }}
    >
      {text}
    </div>
  );
}
