import { API_BASE } from "../constants";
import type { M3FullTestResult } from "../constants";
import type { M3AutoPreviewResult } from "../useM3AutoPreview";

function M3NamingHelpButton({ onOpen }: { onOpen: () => void }) {
  return (
    <button aria-label="查看 M3 图片命名规则" className="iconHelpButton" onClick={onOpen} type="button">?</button>
  );
}

interface M3FullTestViewProps {
  m3FullTestProjectName: string;
  setM3FullTestProjectName: (value: string) => void;
  m3FullTestBulkFiles: File[];
  m3FullTestDescriptions: string;
  setM3FullTestDescriptions: (value: string) => void;
  m3FullTestMessage: string;
  m3FullTestResult: M3FullTestResult | null;
  m3FullAutoPreview: M3AutoPreviewResult;
  busy: boolean;
  updateM3FullTestBulkFiles: (files: File[]) => void;
  runM3FullRenderTest: () => void;
  setM3NamingHelpOpen: (open: boolean) => void;
}

export function M3FullTestView({
  m3FullTestProjectName,
  setM3FullTestProjectName,
  m3FullTestBulkFiles,
  m3FullTestDescriptions,
  setM3FullTestDescriptions,
  m3FullTestMessage,
  m3FullTestResult,
  m3FullAutoPreview,
  busy,
  updateM3FullTestBulkFiles,
  runM3FullRenderTest,
  setM3NamingHelpOpen,
}: M3FullTestViewProps) {
  return (
    <section id="m3-full-test" className="section">
      <div className="sectionHeader">
        <h2>M3完整测试</h2>
        <span className="badge">独立测试</span>
      </div>
      <div className="testPanel">
        <div className="testInputs single">
          <label>项目名称<input value={m3FullTestProjectName} onChange={(event) => setM3FullTestProjectName(event.target.value)} /></label>
        </div>
        <div className="evidenceItem">
          <div>
            <strong>批量 M3 资料自动分类</strong>
            <span className="inlineTitle">文件名格式：项目基本情况-1.jpg / 敏感点路段.xlsx <M3NamingHelpButton onOpen={() => setM3NamingHelpOpen(true)} /></span>
          </div>
          <label className="uploadBox uploadBoxSpaced">
            <span>一次上传 M3 九类图片或 Excel 表格</span>
            <input
              name="m3_full_test_bulk_images"
              type="file"
              multiple
              accept=".xlsx,.png,.jpg,.jpeg,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(event) => updateM3FullTestBulkFiles(Array.from(event.target.files ?? []))}
            />
          </label>
          <div className="fileList">
            {m3FullTestBulkFiles.map((file) => <span key={`m3-bulk-${file.name}`}>{file.name}</span>)}
          </div>
        </div>
        <label>
          批量描述文本（某个图片不需要描述可以不添加，如果添加，冒号前文字要与图片名一一对应）
          <textarea
            value={m3FullTestDescriptions}
            onChange={(event) => {
              setM3FullTestDescriptions(event.target.value);
            }}
            rows={7}
            placeholder={"项目基本情况-1：第一张图片说明\n项目基本情况-2：第二张图片说明\n项目线路图-1：线路图说明"}
          />
        </label>
        {m3FullTestBulkFiles.length > 0 || m3FullTestDescriptions.trim() ? (
          <div className="evidencePanel">
            <div className="sectionHeader">
              <h3>自动匹配预览</h3>
              <span className="badge">按后端规则校验为准</span>
            </div>
            {m3FullAutoPreview.grouped.length ? (
              <div className="evidenceList">
                {m3FullAutoPreview.grouped.map((section) => (
                  <article className="evidenceItem" key={`m3-auto-${section.imageField}`}>
                    <div>
                      <strong>{section.title}</strong>
                      <span>{section.tables.length} 个表格 / {section.files.length} 张图片 / {section.descriptions.length} 条描述</span>
                    </div>
                    <div className="fileList">
                      {section.tables.map((row) => <span key={`auto-table-${section.imageField}-${row.filename}`}>{row.filename}</span>)}
                      {section.files.map((row) => <span key={`auto-file-${section.imageField}-${row.filename}`}>{row.filename}</span>)}
                      {section.descriptions.map((row) => <span key={`auto-desc-${section.imageField}-${row.line}`}>{row.line}</span>)}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="messageLine">尚未识别到可匹配的 M3 表格、图片或描述。</p>
            )}
            {m3FullAutoPreview.unknownFiles.length ? <p className="messageLine errorText">分类不明文件：{m3FullAutoPreview.unknownFiles.join("、")}</p> : null}
            {m3FullAutoPreview.invalidDescriptions.length ? <p className="messageLine errorText">描述格式或分类异常：{m3FullAutoPreview.invalidDescriptions.join("；")}</p> : null}
          </div>
        ) : null}
        <button className="primaryButton" disabled={busy} onClick={runM3FullRenderTest} type="button">执行 M3 完整测试</button>
        <p className="messageLine" style={m3FullTestMessage && m3FullTestMessage.includes("失败") ? {color: "#e74c3c"} : {}}>{m3FullTestMessage}</p>
      </div>

      {m3FullTestResult && m3FullTestResult.ok ? (
        <div className="resultGrid">
          <article className="resultCard">
            <span>渲染状态</span>
            <strong>成功</strong>
            <p>页数：{m3FullTestResult.slide_count} 页</p>
          </article>
          <article className="resultCard wide">
            <span>下载链接</span>
            <strong>M3 完整测试 PPTX 已生成</strong>
            <p>
              <a href={`${API_BASE}${m3FullTestResult.download_url}`} download>点击下载生成的 M3 完整测试 PPTX</a>
            </p>
          </article>
          <article className="resultCard">
            <span>图片数量</span>
            <strong>{Object.values(m3FullTestResult.image_summary || {}).reduce((sum, count) => sum + count, 0)} 张</strong>
            <p>多张图片会自动扩展对应部分页面。</p>
          </article>
          <article className="resultCard">
            <span>表格数量</span>
            <strong>{Object.values(m3FullTestResult.table_summary || {}).reduce((sum, count) => sum + count, 0)} 个</strong>
            <p>同一部分内表格页会排在图片页之前。</p>
          </article>
        </div>
      ) : null}
    </section>
  );
}
