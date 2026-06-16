interface WorkflowStepperProps {
  activeStatus: string;
  hasClassification: boolean;
  hasConfirmed: boolean;
}

const STEPS = [
  { label: "待上传", key: "待上传", sectionId: "projects" },
  { label: "资料解析中", key: "资料解析中", sectionId: "section-upload" },
  { label: "类型识别中", key: "类型识别中", sectionId: "section-upload" },
  { label: "案例匹配中", key: "案例匹配中", sectionId: "section-upload" },
  { label: "待确认", key: "待确认", sectionId: "section-classification" },
  { label: "生成中", key: "生成中", sectionId: "section-generation" },
  { label: "合并中", key: "合并中", sectionId: "section-generation" },
  { label: "完成", key: "完成", sectionId: "section-generation" },
];

const DISPLAY_STEPS = [
  { label: "上传资料", matchKeys: ["待上传"] },
  { label: "识别分析", matchKeys: ["资料解析中", "类型识别中", "案例匹配中"] },
  { label: "人工确认", matchKeys: ["待确认"] },
  { label: "生成PPT", matchKeys: ["生成中", "合并中"] },
  { label: "完成", matchKeys: ["完成"] },
];

export function WorkflowStepper({ activeStatus, hasClassification, hasConfirmed }: WorkflowStepperProps) {
  const currentIndex = STEPS.findIndex((s) => s.key === activeStatus);

  const displayIndex = (() => {
    if (currentIndex < 0) return 0;
    if (activeStatus === "待上传") return 0;
    if (["资料解析中", "类型识别中", "案例匹配中"].includes(activeStatus)) return 1;
    if (activeStatus === "待确认") return 2;
    if (["生成中", "合并中"].includes(activeStatus)) return 3;
    if (activeStatus === "完成") return 4;
    return 0;
  })();

  function handleClick(stepIndex: number) {
    const sectionIds = ["section-upload", "section-upload", "section-classification", "section-generation", "section-generation"];
    const el = document.getElementById(sectionIds[stepIndex]);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="workflow-stepper">
      {DISPLAY_STEPS.map((step, idx) => {
        const isCompleted = idx < displayIndex;
        const isCurrent = idx === displayIndex;
        const stateClass = isCompleted ? "stepper-done" : isCurrent ? "stepper-current" : "stepper-pending";

        return (
          <button
            key={step.label}
            className={`stepper-step ${stateClass}`}
            onClick={() => handleClick(idx)}
            type="button"
            disabled={!isCompleted && !isCurrent}
          >
            <span className="stepper-dot">
              {isCompleted ? "\u2713" : idx + 1}
            </span>
            <span className="stepper-label">{step.label}</span>
          </button>
        );
      })}
    </div>
  );
}
