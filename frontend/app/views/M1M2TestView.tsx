import { Fragment } from "react";
import { projectTypes } from "../constants";
import type { ClassificationResult, StoredFile } from "../constants";
import { labelForProjectType, firstTemplateName } from "../utils";

interface M1M2TestViewProps {
  m1m2TestProjectName: string;
  setM1m2TestProjectName: (value: string) => void;
  m1m2TestFiles: File[];
  setM1m2TestFiles: (files: File[]) => void;
  m1m2TestUploadedFiles: StoredFile[];
  m1m2TestMessage: string;
  m1m2TestResult: ClassificationResult | null;
  m1m2TestReviewStatus: "idle" | "success" | "error";
  m1m2TestGenerateStatus: "idle" | "starting" | "success" | "error";
  m1m2TestTaskStatus: string;
  busy: boolean;
  runM1M2TemplateTest: () => void;
}

export function M1M2TestView({
  m1m2TestProjectName,
  setM1m2TestProjectName,
  m1m2TestFiles,
  setM1m2TestFiles,
  m1m2TestUploadedFiles,
  m1m2TestMessage,
  m1m2TestResult,
  m1m2TestReviewStatus,
  m1m2TestGenerateStatus,
  m1m2TestTaskStatus,
  busy,
  runM1M2TemplateTest,
}: M1M2TestViewProps) {
  return (
    <section id="m1m2-test" className="section">
      <div className="sectionHeader">
        <h2>M1/M2选择测试</h2>
        <span className="badge">固定枚举识别</span>
      </div>
      <div className="testPanel">
        <div className="testInputs single">
          <label>测试项目名称<input value={m1m2TestProjectName} onChange={(event) => setM1m2TestProjectName(event.target.value)} /></label>
        </div>
        <label className="uploadBox">
          <span>上传测试资料</span>
          <input
            name="m1m2_test_files"
            type="file"
            multiple
            accept=".ppt,.pptx,.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
            onChange={(event) => setM1m2TestFiles(Array.from(event.target.files ?? []))}
          />
        </label>
        <div className="fileList">
          {(m1m2TestFiles.length ? m1m2TestFiles : m1m2TestUploadedFiles).map((file) => <span key={"name" in file ? file.name : file.file_id}>{"name" in file ? file.name : file.filename}</span>)}
        </div>
        <button className="primaryButton" disabled={busy} onClick={runM1M2TemplateTest} type="button">识别 M1/M2 类型并选择模板</button>
        <p className="messageLine">{m1m2TestMessage}</p>
      </div>

      <div className="typeCheckGrid">
        {projectTypes.map((item) => (
          <label className={m1m2TestResult?.detected_project_type === item.value ? "typeCheck selected" : "typeCheck"} key={item.value}>
            <input type="radio" checked={m1m2TestResult?.detected_project_type === item.value} readOnly />
            <span>{item.label}</span>
            <small>{item.value}</small>
          </label>
        ))}
      </div>

      <div className="resultGrid">
        <article className="resultCard">
          <span>识别到的项目类型</span>
          <strong>{labelForProjectType(m1m2TestResult?.detected_project_type)}</strong>
          <p>project_type：{m1m2TestResult?.detected_project_type ?? "待识别"}</p>
        </article>
        <article className="resultCard">
          <span>对应 PPT 模板</span>
          <strong>{firstTemplateName(m1m2TestResult?.template_selection?.M1_M2)}</strong>
          <p>只选择既有 M1/M2 固化模板，不动态生成整章内容。</p>
        </article>
        <article className="resultCard">
          <span>confidence</span>
          <strong>{m1m2TestResult?.confidence ? `${Math.round(m1m2TestResult.confidence * 100)}%` : "待识别"}</strong>
          <p>供前端人工确认时参考。</p>
        </article>
        <article className="resultCard">
          <span>matched_keywords</span>
          <strong>{m1m2TestResult?.matched_keywords?.join("、") || "待识别"}</strong>
          <p>命中关键词来自项目名称、文件名和解析文本。</p>
        </article>
        <article className="resultCard">
          <span>分类方式</span>
          <strong>{m1m2TestResult?.classification_method === "llm" ? "LLM" : m1m2TestResult?.classification_method === "rule_fallback" ? "规则 fallback" : "待识别"}</strong>
          <p>{m1m2TestResult?.fallback_reason || "LLM 可用时优先使用模板画像判断。"}</p>
        </article>
        <article className="resultCard">
          <span>LLM 判断理由</span>
          <strong>{m1m2TestResult?.llm_reasoning_summary || "暂无"}</strong>
          <p>模型只判断模板类型，不动态生成 M1/M2 内容。</p>
        </article>
      </div>
      <div className="evidencePanel">
        <div className="sectionHeader">
          <h3>判断依据</h3>
          <span className="badge">detection_evidence</span>
        </div>
        {m1m2TestResult?.detection_evidence?.length ? (
          <div className="evidenceList">
            {m1m2TestResult.detection_evidence.map((item, index) => (
              <article className="evidenceItem" key={`${item.keyword}-${item.source}-${index}`}>
                <div>
                  <strong>{item.keyword || "关键词"}</strong>
                  <span>{item.source || "来源未知"}</span>
                </div>
                <p>{item.snippet || "未返回 snippet"}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="messageLine">未返回明确命中依据，请检查 PDF 是否可提取文本。</p>
        )}
      </div>

      {m1m2TestResult ? (
        <div className="flowStatusPanel">
          <div className="sectionHeader">
            <h3>完整流程状态</h3>
          </div>
          <div className="flowStatusSteps">
            <div className="flowStatusStep">
              <span className={m1m2TestResult ? "flowStatusDot done" : "flowStatusDot"} />
              <span>① 分析识别</span>
            </div>
            <div className="flowStatusStep">
              <span className={m1m2TestReviewStatus === "success" ? "flowStatusDot done" : m1m2TestReviewStatus === "error" ? "flowStatusDot error" : "flowStatusDot"} />
              <span>② 人工确认</span>
              {m1m2TestReviewStatus === "success" && <span className="flowStatusText done">已确认</span>}
              {m1m2TestReviewStatus === "error" && <span className="flowStatusText error">确认失败</span>}
            </div>
            <div className="flowStatusStep">
              <span className={m1m2TestGenerateStatus === "success" ? "flowStatusDot done" : m1m2TestGenerateStatus === "error" ? "flowStatusDot error" : m1m2TestGenerateStatus === "starting" ? "flowStatusDot running" : "flowStatusDot"} />
              <span>③ 启动生成</span>
              {m1m2TestGenerateStatus === "success" && <span className="flowStatusText done">{m1m2TestTaskStatus}</span>}
              {m1m2TestGenerateStatus === "error" && <span className="flowStatusText error">生成失败</span>}
              {m1m2TestGenerateStatus === "starting" && <span className="flowStatusText running">进行中...</span>}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
