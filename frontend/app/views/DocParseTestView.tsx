import { Fragment } from "react";
import type { ClassificationResult } from "../constants";
import { labelForProjectType, firstTemplateName } from "../utils";

interface DocParseTestViewProps {
  docParseTestFiles: File[];
  setDocParseTestFiles: (files: File[]) => void;
  docParseTestMessage: string;
  docParseTestResult: ClassificationResult | null;
  docParseTestExpandedFiles: Record<number, boolean>;
  docParseTestLoadingFullText: Record<number, boolean>;
  docParseTestFullTextMap: Record<number, string>;
  busy: boolean;
  runDocumentParseTest: () => void;
  toggleDocParseTestFileExpanded: (fileId: number) => void;
}

export function DocParseTestView({
  docParseTestFiles,
  setDocParseTestFiles,
  docParseTestMessage,
  docParseTestResult,
  docParseTestExpandedFiles,
  docParseTestLoadingFullText,
  docParseTestFullTextMap,
  busy,
  runDocumentParseTest,
  toggleDocParseTestFileExpanded,
}: DocParseTestViewProps) {
  return (
    <section id="document-parse-test" className="section">
      <div className="sectionHeader">
        <h2>文档解析测试</h2>
        <span className="badge">真实流程验证</span>
      </div>
      <div className="testPanel">
        <label className="uploadBox">
          <span>选择测试文件</span>
          <input
            name="document_parse_test_files"
            type="file"
            multiple
            accept=".txt,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg,.dwg,.dxf"
            onChange={(event) => setDocParseTestFiles(Array.from(event.target.files ?? []))}
          />
        </label>
        <div className="fileList">
          {docParseTestFiles.map((file) => <span key={file.name}>{file.name}</span>)}
        </div>
        <button className="primaryButton" disabled={busy} onClick={runDocumentParseTest} type="button">开始解析测试</button>
        <p className="messageLine">{docParseTestMessage}</p>
      </div>

      {docParseTestResult ? (
        <div className="parseTestResults">
          <div className="resultGrid">
            <article className="resultCard">
              <span>项目类型</span>
              <strong>{labelForProjectType(docParseTestResult.detected_project_type)}</strong>
              <p>置信度: {docParseTestResult.confidence ? `${Math.round(docParseTestResult.confidence * 100)}%` : "N/A"}</p>
            </article>
            <article className="resultCard">
              <span>匹配关键词</span>
              <strong>{docParseTestResult.matched_keywords?.join("、") || "暂无"}</strong>
              <p>用于判断向量相关性</p>
            </article>
            <article className="resultCard">
              <span>M1/M2 模板</span>
              <strong>{firstTemplateName(docParseTestResult.template_selection?.M1_M2)}</strong>
              <p>模板选择结果</p>
            </article>
            <article className="resultCard">
              <span>M5 案例数</span>
              <strong>{docParseTestResult.case_selection?.recommended_cases?.length ?? 0} 个</strong>
              <p>{docParseTestResult.case_selection?.status || ""}</p>
            </article>
          </div>
          {docParseTestResult.files && docParseTestResult.files.length > 0 ? (
            <div className="doc-parse-table-wrapper">
              <h3 className="doc-parse-table-title">
                文件解析详情（共 {docParseTestResult.files.length} 个文件）
              </h3>
              <table className="doc-parse-table">
                <thead>
                  <tr className="doc-parse-table-header-row">
                    <th className="doc-parse-table-header-cell">文件名</th>
                    <th className="doc-parse-table-header-cell">解析状态</th>
                    <th className="doc-parse-table-header-cell">资料角色</th>
                    <th className="doc-parse-table-header-cell">服务模块</th>
                    <th className="doc-parse-table-header-cell">解析文本</th>
                  </tr>
                </thead>
                <tbody>
                  {docParseTestResult.files.map((f, idx) => (
                    <Fragment key={idx}>
                      <tr className="doc-parse-table-row">
                        <td className="doc-parse-table-cell">{f.filename}</td>
                        <td className="doc-parse-table-cell">
                          <span className={`parseStatus ${f.parse_status}`}>{f.parse_status}</span>
                          {f.parse_status === "pending_enhancement" && <span className="badge warn doc-parse-status-extra">待增强</span>}
                          {f.parse_status === "pending_ocr" && <span className="badge warn doc-parse-status-extra">待OCR</span>}
                          {f.parse_status === "failed" && <span className="badge warn doc-parse-status-extra">失败</span>}
                        </td>
                        <td className="doc-parse-table-cell text-muted">{f.document_role || "未知"}</td>
                        <td className="doc-parse-table-cell text-muted">{(f.assigned_modules || []).join(", ") || "未分配"}</td>
                        <td className="doc-parse-table-cell">
                          {f.parse_status === "parsed" ? (
                            f.text_preview ? (
                              <button
                                className="btn-doc-action"
                                onClick={() => toggleDocParseTestFileExpanded(f.file_id)}
                                type="button"
                              >
                                {docParseTestExpandedFiles[f.file_id] ? "收起" : "查看文本"}
                              </button>
                            ) : (
                              <span className="doc-parse-loading-text">解析成功，无文本内容</span>
                            )
                          ) : f.error_message ? (
                            <span className="doc-parse-error-text" title={f.error_message}>{f.error_message.length > 30 ? f.error_message.slice(0, 30) + "…" : f.error_message}</span>
                          ) : (
                            <span className="doc-parse-loading-text">暂无解析文本</span>
                          )}
                        </td>
                      </tr>
                      {docParseTestExpandedFiles[f.file_id] ? (
                        <tr key={`${idx}-text`}>
                          <td colSpan={5} className="doc-parse-expanded-cell">
                            {docParseTestLoadingFullText[f.file_id] ? (
                              <span className="doc-parse-loading-text">加载中…</span>
                            ) : (
                              <pre className="doc-parse-expanded-pre">
                                {docParseTestFullTextMap[f.file_id] || "（空）"}
                              </pre>
                            )}
                          </td>
                        </tr>
                      ) : null}
                      {f.parse_status === "parsed" && f.text_preview && !docParseTestExpandedFiles[f.file_id] ? (
                        <tr key={`${idx}-preview`}>
                          <td colSpan={5} className="doc-parse-preview-cell">
                            <span className="doc-parse-preview-label">文本预览：</span>
                            <span className="doc-parse-preview-text">{f.text_preview}{f.text_preview.length >= 1500 ? "…" : ""}</span>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
