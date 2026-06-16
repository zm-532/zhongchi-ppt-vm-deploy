import { M3_FULL_SECTIONS } from "../constants";
import type { M3MaterialsResult, Project } from "../constants";
import type { M3AutoPreviewResult } from "../useM3AutoPreview";
import { Breadcrumb } from "../components/Breadcrumb";

function M3NamingHelpButton({ onOpen }: { onOpen: () => void }) {
  return (
    <button aria-label="查看 M3 图片命名规则" className="iconHelpButton" onClick={onOpen} type="button">?</button>
  );
}

interface M3MaterialsViewProps {
  currentProject: Project | null;
  m3MaterialsResult: M3MaterialsResult | null;
  m3MaterialBulkFiles: File[];
  m3MaterialDescriptions: string;
  setM3MaterialDescriptions: (value: string) => void;
  m3MaterialsMessage: string;
  m3MaterialAutoPreview: M3AutoPreviewResult;
  busy: boolean;
  updateM3MaterialBulkFiles: (files: File[]) => void;
  saveM3Materials: (returnToProjects?: boolean) => void;
  setM3NamingHelpOpen: (open: boolean) => void;
}

export function M3MaterialsView({
  currentProject,
  m3MaterialsResult,
  m3MaterialBulkFiles,
  m3MaterialDescriptions,
  setM3MaterialDescriptions,
  m3MaterialsMessage,
  m3MaterialAutoPreview,
  busy,
  updateM3MaterialBulkFiles,
  saveM3Materials,
  setM3NamingHelpOpen,
}: M3MaterialsViewProps) {
  return (
    <section id="project-m3-materials" className="section">
      <Breadcrumb
        items={[
          { label: "我的项目", href: "#projects" },
          ...(currentProject ? [{ label: currentProject.project_name, href: "#projects" }] : []),
          { label: "M3资料上传" },
        ]}
      />
      <div className="sectionHeader">
        <h2>M3资料上传</h2>
        <span className="badge">正式流程</span>
      </div>
      {currentProject ? (
        <div className="testPanel">
          <div className="m3-material-page-header">
            <div>
              <strong style={{ fontSize: 17 }}>{currentProject.project_name}</strong>
              <span>
                {currentProject.project_location ? `${currentProject.project_location} · ` : ""}
                {currentProject.product_line || ""}
                {currentProject.project_location || currentProject.product_line ? " · " : ""}
                已填写 {m3MaterialsResult?.text_completed_count ?? 0}/{m3MaterialsResult?.text_total_count ?? 9} 个部分，已上传 {m3MaterialsResult?.image_count ?? 0} 张图片 / {m3MaterialsResult?.table_count ?? 0} 个表格
              </span>
            </div>
            <a className="secondaryButton" href="#projects">返回我的项目</a>
          </div>
          <div className="evidenceItem">
            <div>
              <strong>批量 M3 资料自动分类</strong>
              <span className="inlineTitle">文件名格式：项目基本情况-1.jpg / 现场勘查情况.xlsx <M3NamingHelpButton onOpen={() => setM3NamingHelpOpen(true)} /></span>
            </div>
            <label className="uploadBox uploadBoxSpaced">
              <span>一次上传 M3 九类图片或 Excel 表格</span>
              <input
                name="project_m3_material_bulk_images"
                type="file"
                multiple
                accept=".xlsx,.png,.jpg,.jpeg,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(event) => updateM3MaterialBulkFiles(Array.from(event.target.files ?? []))}
              />
            </label>
            <div className="fileList">
              {(m3MaterialBulkFiles.length
                ? m3MaterialBulkFiles.map((file) => file.name)
                : [...(m3MaterialsResult?.tables || []).map((table) => table.filename), ...(m3MaterialsResult?.images || []).map((image) => image.filename)]
              ).map((name) => (
                <span key={`project-m3-material-${name}`}>{name}</span>
              ))}
            </div>
          </div>
          <label>
            批量描述文本（某个图片不需要描述可以不添加，如果添加，冒号前文字要与图片名一一对应）
            <textarea
              value={m3MaterialDescriptions}
              onChange={(event) => {
                setM3MaterialDescriptions(event.target.value);
              }}
              rows={7}
              placeholder={"项目基本情况-1：第一张图片说明\n项目基本情况-2：第二张图片说明\n项目线路图-1：线路图说明"}
            />
          </label>
          {m3MaterialBulkFiles.length > 0 || m3MaterialDescriptions.trim() ? (
            <div className="evidencePanel">
              <div className="sectionHeader">
                <h3>自动匹配预览</h3>
                <span className="badge">保存时由后端校验</span>
              </div>
              {m3MaterialAutoPreview.grouped.length ? (
                <div className="evidenceList">
                  {m3MaterialAutoPreview.grouped.map((section) => (
                    <article className="evidenceItem" key={`project-m3-auto-${section.imageField}`}>
                      <div>
                        <strong>{section.title}</strong>
                        <span>{section.tables.length} 个表格 / {section.files.length} 张图片 / {section.descriptions.length} 条描述</span>
                      </div>
                      <div className="fileList">
                        {section.tables.map((row) => <span key={`project-auto-table-${section.imageField}-${row.filename}`}>{row.filename}</span>)}
                        {section.files.map((row) => <span key={`project-auto-file-${section.imageField}-${row.filename}`}>{row.filename}</span>)}
                        {section.descriptions.map((row) => <span key={`project-auto-desc-${section.imageField}-${row.line}`}>{row.line}</span>)}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="messageLine">尚未识别到可匹配的 M3 表格、图片或描述。</p>
              )}
              {m3MaterialAutoPreview.unknownFiles.length ? <p className="messageLine errorText">分类不明文件：{m3MaterialAutoPreview.unknownFiles.join("、")}</p> : null}
              {m3MaterialAutoPreview.invalidDescriptions.length ? <p className="messageLine errorText">描述格式或分类异常：{m3MaterialAutoPreview.invalidDescriptions.join("；")}</p> : null}
            </div>
          ) : null}
          <div className="evidenceList">
            {M3_FULL_SECTIONS.map((section) => {
              const savedImages = (m3MaterialsResult?.images || []).filter((image) => image.purpose === section.imageField);
              const savedTables = (m3MaterialsResult?.tables || []).filter((table) => table.purpose === section.imageField);
              if (!savedImages.length && !savedTables.length) return null;
              return (
                <article className="evidenceItem" key={`project-saved-${section.textField}`}>
                  <div>
                    <strong>{section.title}</strong>
                    <span>{savedTables.length} 个已保存表格 / {savedImages.length} 张已保存图片</span>
                  </div>
                  <div className="fileList">
                    {savedTables.map((table) => <span key={`${section.imageField}-saved-table-${table.stored_path}`}>{table.filename}</span>)}
                    {savedImages.map((image) => <span key={`${section.imageField}-saved-${image.stored_path}`}>{image.filename}{image.description ? `：${image.description}` : ""}</span>)}
                  </div>
                </article>
              );
            })}
          </div>
          <div className="upload-actions-bar">
            <button className="primaryButton" disabled={busy} onClick={() => saveM3Materials(false)} type="button">保存M3资料</button>
            <button className="primaryButton" disabled={busy} onClick={() => saveM3Materials(true)} type="button">保存并返回我的项目</button>
            <a className="secondaryButton" href="#projects">返回我的项目</a>
          </div>
          <p className="messageLine" style={m3MaterialsMessage && m3MaterialsMessage.includes("失败") ? {color: "#e74c3c"} : {}}>{m3MaterialsMessage}</p>
        </div>
      ) : (
        <div className="emptyState compact"><h3>请先选择项目</h3><p>回到我的项目页面选择一个项目后，再进入 M3资料上传。</p><a className="secondaryButton" href="#projects">返回我的项目</a></div>
      )}
    </section>
  );
}
