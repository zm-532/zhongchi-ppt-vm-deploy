import { API_BASE } from "../constants";
import type { CaseLibraryItem, FullPptCaseItem } from "../constants";
import { labelForProjectType, formatFileSize, formatStoredAt } from "../utils";

interface CaseLibraryViewProps {
  caseLibraryTab: "m5" | "full-ppt";
  setCaseLibraryTab: (tab: "m5" | "full-ppt") => void;
  m5FixedCases: CaseLibraryItem[];
  fullPptCases: FullPptCaseItem[];
}

export function CaseLibraryView({ caseLibraryTab, setCaseLibraryTab, m5FixedCases, fullPptCases }: CaseLibraryViewProps) {
  return (
    <section id="cases" className="section">
      <div className="sectionHeader"><h2>案例库管理</h2><button className="secondaryButton" disabled type="button">新增案例</button></div>
      <div className="caseLibraryTabs" role="tablist" aria-label="案例库分类">
        <button className={caseLibraryTab === "m5" ? "caseLibraryTab active" : "caseLibraryTab"} onClick={() => setCaseLibraryTab("m5")} role="tab" type="button">M5案例库</button>
        <button className={caseLibraryTab === "full-ppt" ? "caseLibraryTab active" : "caseLibraryTab"} onClick={() => setCaseLibraryTab("full-ppt")} role="tab" type="button">完整PPT案例库</button>
      </div>
      {caseLibraryTab === "m5" ? (
        m5FixedCases.length > 0 ? (
          <div className="evidenceList">
            {m5FixedCases.map((item) => (
              <article className="evidenceItem" key={item.case_id}>
                <div>
                  <strong>{item.filename || item.title}</strong>
                  <span>case_id: {String(item.case_id)}</span>
                </div>
                {item.project_type ? <p>项目类型：{item.project_type}</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <div className="cases-empty-panel">
            <h3 className="cases-empty-title">暂未发现 M5 案例文件</h3>
            <p className="cases-empty-desc">请检查 ppt_engine/templates/solution_fixed_modules/M5 目录下是否存在 .pptx 案例文件。</p>
            <div className="cases-capability-list">
              <div className="cases-capability-item">历史项目案例归档</div>
              <div className="cases-capability-item">项目标签与场景匹配</div>
              <div className="cases-capability-item">M5 推荐案例辅助生成</div>
            </div>
          </div>
        )
      ) : (
        fullPptCases.length > 0 ? (
          <div className="evidenceList">
            {fullPptCases.map((caseItem) => (
              <article className="evidenceItem fullPptCaseItem" key={caseItem.case_id}>
                <div>
                  <strong>{caseItem.title || caseItem.filename}</strong>
                  <span>{caseItem.filename}</span>
                  <span>{formatFileSize(caseItem.file_size)}</span>
                </div>
                <p>项目类型：{labelForProjectType(caseItem.project_type)}；存入时间：{formatStoredAt(caseItem.stored_at)}</p>
                <p className="sourcePath">case_id: {caseItem.case_id}</p>
                <div className="caseItemActions">
                  <a className="secondaryButton btn-xs" href={`${API_BASE}/api/cases/full-ppt/${caseItem.case_id}/download`} download>下载 PPTX</a>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="cases-empty-panel">
            <h3 className="cases-empty-title">暂未保存完整PPT案例</h3>
            <p className="cases-empty-desc">在项目完整生成后，点击最终文件区域的"存入案例库"，即可在这里查看和下载。</p>
            <div className="cases-capability-list">
              <div className="cases-capability-item">完整PPT归档</div>
              <div className="cases-capability-item">按项目保留最新版本</div>
              <div className="cases-capability-item">案例库下载复用</div>
            </div>
          </div>
        )
      )}
    </section>
  );
}
