import type { ClassificationResult, StoredFile } from "../constants";
import { labelForProjectType } from "../utils";

interface M5TestViewProps {
  m5TestProjectName: string;
  setM5TestProjectName: (value: string) => void;
  m5TestFiles: File[];
  setM5TestFiles: (files: File[]) => void;
  m5TestUploadedFiles: StoredFile[];
  m5TestMessage: string;
  m5TestResult: ClassificationResult | null;
  m5TestReviewStatus: "idle" | "success" | "error";
  m5TestGenerateStatus: "idle" | "starting" | "success" | "error";
  m5TestTaskStatus: string;
  busy: boolean;
  runM5CaseTest: () => void;
}

export function M5TestView({
  m5TestProjectName,
  setM5TestProjectName,
  m5TestFiles,
  setM5TestFiles,
  m5TestUploadedFiles,
  m5TestMessage,
  m5TestResult,
  m5TestReviewStatus,
  m5TestGenerateStatus,
  m5TestTaskStatus,
  busy,
  runM5CaseTest,
}: M5TestViewProps) {
  return (
    <section id="m5-test" className="section">
      <div className="sectionHeader">
        <h2>M5选择测试</h2>
        <span className="badge">案例库匹配</span>
      </div>
      <div className="testPanel">
        <div className="testInputs single">
          <label>测试项目名称<input value={m5TestProjectName} onChange={(event) => setM5TestProjectName(event.target.value)} /></label>
        </div>
        <label className="uploadBox">
          <span>上传测试资料</span>
          <input
            name="m5_test_files"
            type="file"
            multiple
            accept=".ppt,.pptx,.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
            onChange={(event) => setM5TestFiles(Array.from(event.target.files ?? []))}
          />
        </label>
        <div className="fileList">
          {(m5TestFiles.length ? m5TestFiles : m5TestUploadedFiles).map((file) => <span key={"name" in file ? file.name : file.file_id}>{"name" in file ? file.name : file.filename}</span>)}
        </div>
        <button className="primaryButton" disabled={busy} onClick={runM5CaseTest} type="button">分析并匹配案例</button>
        <p className="messageLine">{m5TestMessage}</p>
      </div>

      <div className="resultGrid">
        <article className="resultCard">
          <span>项目类型</span>
          <strong>{labelForProjectType(m5TestResult?.detected_project_type)}</strong>
          <p>用于筛选同类项目案例</p>
        </article>
        <article className="resultCard">
          <span>推荐案例数</span>
          <strong>{m5TestResult?.case_selection?.recommended_cases?.length ?? 0} 个</strong>
          <p>系统根据项目标签匹配相似案例</p>
        </article>
      </div>

      {m5TestResult?.case_selection?.recommended_cases && m5TestResult.case_selection.recommended_cases.length > 0 ? (
        <div className="evidencePanel">
          <div className="sectionHeader">
            <h3>匹配结果</h3>
            <span className="badge">recommended_cases</span>
          </div>
          <div className="evidenceList">
            {m5TestResult.case_selection.recommended_cases.map((caseItem, index) => (
              <article className="evidenceItem" key={caseItem.case_id ?? index}>
                <div>
                  <strong>{caseItem.title || `案例 ${index + 1}`}</strong>
                  <span>case_id: {String(caseItem.case_id)}</span>
                </div>
                <p><strong>匹配理由：</strong>{caseItem.match_reason || "暂无匹配理由"}</p>
                <div>
                  <strong>匹配标签：</strong>
                  {caseItem.matched_tags && caseItem.matched_tags.length > 0 ? (
                    caseItem.matched_tags.map((tag, tagIndex) => (
                      <span className="caseTag" key={tagIndex}>{tag}</span>
                    ))
                  ) : (
                    <span>暂无标签</span>
                  )}
                </div>
                {caseItem.source_path && (
                  <p className="sourcePath"><strong>来源路径：</strong>{caseItem.source_path}</p>
                )}
              </article>
            ))}
          </div>
        </div>
      ) : (
        <div className="emptyState compact">
          <h3>暂无高匹配案例</h3>
          <p>{m5TestResult?.case_selection?.message || "系统未找到相似案例，可能原因：1) 案例库为空；2) 上传资料不完整；3) 项目类型与现有案例差异较大。"}</p>
        </div>
      )}

      {m5TestResult?.case_selection?.status && (
        <div className={m5TestResult.case_selection.status === "matched" ? "matchStatus matched" : "matchStatus"}>
          <strong>案例匹配状态：</strong>{m5TestResult.case_selection.status}
          {m5TestResult.case_selection.message && <span> - {m5TestResult.case_selection.message}</span>}
        </div>
      )}

      {m5TestResult?.detection_evidence && m5TestResult.detection_evidence.length > 0 && (
        <div className="evidencePanel spaced">
          <div className="sectionHeader">
            <h3>判断依据</h3>
            <span className="badge">detection_evidence</span>
          </div>
          <div className="evidenceList">
            {m5TestResult.detection_evidence.map((item, index) => (
              <article className="evidenceItem" key={`${item.keyword}-${item.source}-${index}`}>
                <div>
                  <strong>{item.keyword || "关键词"}</strong>
                  <span>{item.source || "来源未知"}</span>
                </div>
                <p>{item.snippet || "未返回 snippet"}</p>
              </article>
            ))}
          </div>
        </div>
      )}

      {m5TestResult ? (
        <div className="flowStatusPanel">
          <div className="sectionHeader">
            <h3>完整流程状态</h3>
          </div>
          <div className="flowStatusSteps">
            <div className="flowStatusStep">
              <span className={m5TestResult ? "flowStatusDot done" : "flowStatusDot"} />
              <span>① 分析识别</span>
            </div>
            <div className="flowStatusStep">
              <span className={m5TestReviewStatus === "success" ? "flowStatusDot done" : m5TestReviewStatus === "error" ? "flowStatusDot error" : "flowStatusDot"} />
              <span>② 人工确认</span>
              {m5TestReviewStatus === "success" && <span className="flowStatusText done">已确认</span>}
              {m5TestReviewStatus === "error" && <span className="flowStatusText error">确认失败</span>}
            </div>
            <div className="flowStatusStep">
              <span className={m5TestGenerateStatus === "success" ? "flowStatusDot done" : m5TestGenerateStatus === "error" ? "flowStatusDot error" : m5TestGenerateStatus === "starting" ? "flowStatusDot running" : "flowStatusDot"} />
              <span>③ 启动生成</span>
              {m5TestGenerateStatus === "success" && <span className="flowStatusText done">{m5TestTaskStatus}</span>}
              {m5TestGenerateStatus === "error" && <span className="flowStatusText error">生成失败</span>}
              {m5TestGenerateStatus === "starting" && <span className="flowStatusText running">进行中...</span>}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
