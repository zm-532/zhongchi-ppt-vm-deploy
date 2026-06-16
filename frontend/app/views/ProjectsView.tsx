import { projectTypes, m1m2Templates, M3_FULL_SECTIONS, M3_SECTION_TITLE_ALIASES, PROJECT_LIST_PREVIEW_LIMIT, PROJECT_LIST_PAGE_SIZE } from "../constants";
import type { Project, ClassificationResult, CaseLibraryItem, CaseSelection, QualityReport, M3MaterialsResult, TaskState, ReviewForm, StoredFile } from "../constants";
import { labelForProjectType, firstTemplateName, getProjectStatusClass, qualityReportLabel, projectTypeFromProductLine } from "../utils";
import type { M3AutoPreviewResult } from "../useM3AutoPreview";

function M3NamingHelpButton({ onOpen }: { onOpen: () => void }) {
  return (
    <button aria-label="查看 M3 图片命名规则" className="iconHelpButton" onClick={onOpen} type="button">?</button>
  );
}

interface ProjectsViewProps {
  projects: Project[];
  currentProject: Project | null;
  setCurrentProject: (project: Project) => void;
  task: TaskState | null;
  setTask: (task: TaskState | null) => void;
  classification: ClassificationResult | null;
  setClassification: (c: ClassificationResult | null) => void;
  showClassificationDetails: boolean;
  setShowClassificationDetails: (show: boolean) => void;
  qualityReportExpanded: boolean;
  setQualityReportExpanded: (expanded: boolean) => void;
  reviewForm: ReviewForm;
  setReviewForm: React.Dispatch<React.SetStateAction<ReviewForm>>;
  recommendedCases: NonNullable<CaseSelection["recommended_cases"]>;
  m5FixedCases: CaseLibraryItem[];
  canSaveFullPptCase: boolean;
  productLineClassificationConflict: { productLine: string; preferredProjectType: string; detectedProjectType: string } | null;
  hasMoreProjects: boolean;
  totalProjectPages: number;
  visibleProjects: Project[];
  projectListExpanded: boolean;
  setProjectListExpanded: React.Dispatch<React.SetStateAction<boolean>>;
  projectListPage: number;
  setProjectListPage: (page: number) => void;
  isManagingProjects: boolean;
  selectedProjectIds: number[];
  activeStatus: string;
  statusHistory: string;
  qualityReport: QualityReport | undefined;
  message: string;
  busy: boolean;
  uploadSuccess: boolean;
  selectedFiles: File[];
  setSelectedFiles: (files: File[]) => void;
  uploadedFiles: StoredFile[];
  isEditingProject: boolean;
  setIsEditingProject: (editing: boolean) => void;
  editForm: { project_name: string; project_location: string; owner_unit: string; product_line: string };
  setEditForm: React.Dispatch<React.SetStateAction<{ project_name: string; project_location: string; owner_unit: string; product_line: string }>>;
  m3MaterialsResult: M3MaterialsResult | null;
  previewLoading: boolean;
  m3MaterialAutoPreview: M3AutoPreviewResult;
  toggleProjectManagement: () => void;
  toggleProjectSelection: (projectId: number) => void;
  deleteSelectedProjects: () => void;
  uploadProjectFiles: () => void;
  analyzeProject: () => void;
  submitClassificationReview: () => void;
  generate: () => void;
  saveFullPptCase: () => void;
  previewFinalPpt: () => void;
  downloadFinal: () => void;
  updateProjectBasicInfo: () => void;
  setM3NamingHelpOpen: (open: boolean) => void;
}

export function ProjectsView(props: ProjectsViewProps) {
  const {
    projects, currentProject, setCurrentProject, task, setTask, classification, setClassification,
    showClassificationDetails, setShowClassificationDetails, qualityReportExpanded, setQualityReportExpanded,
    reviewForm, setReviewForm, recommendedCases, m5FixedCases, canSaveFullPptCase,
    productLineClassificationConflict, hasMoreProjects, totalProjectPages, visibleProjects,
    projectListExpanded, setProjectListExpanded, projectListPage, setProjectListPage,
    isManagingProjects, selectedProjectIds, activeStatus, statusHistory, qualityReport,
    message, busy, uploadSuccess, selectedFiles, setSelectedFiles, uploadedFiles,
    isEditingProject, setIsEditingProject, editForm, setEditForm, m3MaterialsResult,
    previewLoading, toggleProjectManagement, toggleProjectSelection, deleteSelectedProjects,
    uploadProjectFiles, analyzeProject, submitClassificationReview, generate,
    saveFullPptCase, previewFinalPpt, downloadFinal, updateProjectBasicInfo,
  } = props;

  return (
    <>
      <section id="projects" className="section">
        <div className="sectionHeader"><h2>项目列表</h2><span className="badge">{projects.length ? `${projects.length} 个项目` : "Demo 数据"}</span></div>
        {projects.length === 0 ? <div className="emptyState"><div className="emptyIcon" aria-hidden="true">+</div><h3>还没有任何项目</h3><p>点击右上角新建项目，填写基础信息后即可进入资料上传。</p><a className="secondaryButton" href="#create">创建第一个项目</a></div> : (
          <>
            {isManagingProjects ? (
              <div className="projectManageBar"><span>已选择 {selectedProjectIds.length} 个项目</span><button className="dangerButton" disabled={busy || selectedProjectIds.length === 0} onClick={deleteSelectedProjects} type="button">删除选中</button></div>
            ) : null}
            <div className="projectList">{visibleProjects.map((project) => isManagingProjects ? (
              <label className={selectedProjectIds.includes(project.project_id) ? "projectItem manageItem selected" : "projectItem manageItem"} key={project.project_id}>
                <input checked={selectedProjectIds.includes(project.project_id)} onChange={() => toggleProjectSelection(project.project_id)} type="checkbox" />
                <strong>{project.project_name}</strong>
                <span className={`project-status-badge ${getProjectStatusClass(project.task_status)}`}>{project.task_status}</span>
              </label>
            ) : (
              <button className={currentProject?.project_id === project.project_id ? "projectItem selected" : "projectItem"} key={project.project_id} onClick={() => { setCurrentProject(project); setTask(null); setClassification(null); setShowClassificationDetails(false); setReviewForm({ projectType: "", m1m2Template: "", caseId: undefined, m3Selection: "m3_template", includePrintTailPage: false, notes: "" }); }} type="button"><strong>{project.project_name}</strong><span className={`project-status-badge ${getProjectStatusClass(project.task_status)}`}>{project.task_status}</span></button>
            ))}</div>
            {hasMoreProjects ? (
              <div className="projectListFooter">
                <span>{projectListExpanded ? `第 ${projectListPage} / ${totalProjectPages} 页，共 ${projects.length} 个项目` : `已显示前 ${PROJECT_LIST_PREVIEW_LIMIT} 个，共 ${projects.length} 个项目`}</span>
                <div className="projectListFooterActions">
                  {projectListExpanded && totalProjectPages > 1 ? (
                    <>
                      <button className="secondaryButton" disabled={projectListPage <= 1} onClick={() => setProjectListPage(Math.max(1, projectListPage - 1))} type="button">上一页</button>
                      <button className="secondaryButton" disabled={projectListPage >= totalProjectPages} onClick={() => setProjectListPage(Math.min(totalProjectPages, projectListPage + 1))} type="button">下一页</button>
                    </>
                  ) : null}
                  <button className="secondaryButton" onClick={() => { setProjectListExpanded(!projectListExpanded); setProjectListPage(1); }} type="button">
                    {projectListExpanded ? "收起" : "显示更多"}
                  </button>
                </div>
              </div>
            ) : null}
          </>
        )}
      </section>

      {currentProject ? (
        <>
          <section className="section">
            <div className="sectionHeader"><h2>统一资料上传</h2><span className="badge">支持多文件</span></div>
            <div className="uploadPanel">
              <div>
                {isEditingProject ? (
                  <div className="project-info-edit-panel">
                    <input
                      value={editForm.project_name}
                      onChange={(e) => setEditForm((f) => ({ ...f, project_name: e.target.value }))}
                      placeholder="项目名称"
                      className="project-info-edit-input"
                    />
                    <input
                      value={editForm.project_location}
                      onChange={(e) => setEditForm((f) => ({ ...f, project_location: e.target.value }))}
                      placeholder="项目所在地"
                      className="project-info-edit-input"
                    />
                    <input
                      value={editForm.owner_unit}
                      onChange={(e) => setEditForm((f) => ({ ...f, owner_unit: e.target.value }))}
                      placeholder="建设/业主单位"
                      className="project-info-edit-input"
                    />
                    <input
                      value={editForm.product_line}
                      onChange={(e) => setEditForm((f) => ({ ...f, product_line: e.target.value }))}
                      placeholder="产品线"
                      className="project-info-edit-input"
                    />
                    <div className="project-info-edit-actions">
                      <button className="primaryButton btn-xs" disabled={busy} onClick={updateProjectBasicInfo} type="button">保存</button>
                      <button className="secondaryButton btn-xs" disabled={busy} onClick={() => setIsEditingProject(false)} type="button">取消</button>
                    </div>
                  </div>
                ) : (
                  <div className="project-info-header">
                    <h3>{currentProject.project_name}</h3>
                    <button
                      className="secondaryButton btn-xs-pad"
                      onClick={() => {
                        setEditForm({
                          project_name: currentProject.project_name || "",
                          project_location: currentProject.project_location || "",
                          owner_unit: currentProject.owner_unit || "",
                          product_line: currentProject.product_line || "",
                        });
                        setIsEditingProject(true);
                      }}
                      type="button"
                    >
                      编辑基础信息
                    </button>
                  </div>
                )}
                <p>系统将自动识别资料用途，上传时无需选择资料归属章节。</p>
                <p className="uploadHint">支持格式：.ppt / .pptx / .pdf / .doc / .docx / .xls / .xlsx / .png / .jpg / .jpeg</p>
              </div>
              <label className="uploadBox">
                <span>选择项目资料</span>
                <input
                  name="project_files"
                  type="file"
                  multiple
                  accept=".ppt,.pptx,.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
                  onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
                />
              </label>
              <div className="fileList">
                {(selectedFiles.length ? selectedFiles : uploadedFiles).map((file) => <span key={"name" in file ? file.name : file.file_id}>{"name" in file ? file.name : file.filename}</span>)}
              </div>
            </div>
            <div className="m3-material-entry">
              <div>
                <strong>M3资料上传</strong>
                <span>用于项目深化方案 M3 章节生成</span>
              </div>
              <p className="m3-upload-summary"><strong>M3上传情况：</strong>已填写 {m3MaterialsResult?.text_completed_count ?? 0}/{m3MaterialsResult?.text_total_count ?? 9} 个部分，已上传 {m3MaterialsResult?.image_count ?? 0} 张图片</p>
              <a className="secondaryButton" href="#project-m3-materials">进入M3资料上传</a>
            </div>
            {uploadSuccess && <div className="uploadSuccess">上传成功</div>}
            <div className="upload-actions-bar">
              <button className="primaryButton" disabled={busy} onClick={uploadProjectFiles} type="button">统一上传项目资料</button>
              <button className="secondaryButton" disabled={busy} onClick={analyzeProject} type="button">开始识别资料</button>
            </div>
          </section>

          <section className="section">
            <div className="sectionHeader"><h2>识别结果确认</h2><span className="badge">确认项目类型与模板</span></div>
            {classification ? (
              <>
                <div className="resultGrid">
                  <article className="resultCard">
                    <span>项目类型</span>
                    <strong>{labelForProjectType(classification.detected_project_type)}</strong>
                    <p>置信度：{classification.confidence ? `${Math.round(classification.confidence * 100)}%` : "待返回"}；关键词：{classification.matched_keywords?.join("、") || "暂无"}</p>
                  </article>
                  <article className="resultCard">
                    <span>M1/M2 选用模板</span>
                    <strong>{firstTemplateName(classification.template_selection?.M1_M2)}</strong>
                    <p>用于行业背景、技术标准、项目概况与现场挑战的固化模板字段替换。</p>
                    <button className="secondaryButton btn-xs" onClick={() => setShowClassificationDetails(!showClassificationDetails)} type="button">{showClassificationDetails ? "收起分析依据" : "查看分析依据"}</button>
                  </article>
                  <article className="resultCard">
                    <span>M5 推荐案例</span>
                    <strong>{recommendedCases[0]?.title || recommendedCases[0]?.source_path?.split(/[\\/]/).pop() || "暂无推荐案例"}</strong>
                    <p>{recommendedCases[0]?.match_reason ?? "暂无推荐案例，可在下方人工确认中选择 M5 案例或暂不选择。"}</p>
                  </article>
                  <article className="resultCard">
                    <span>M6 固定模板</span>
                    <strong>{firstTemplateName(classification.template_selection?.M6)}</strong>
                    <p>默认使用企业背书与荣誉固定模板，可由后端补充替换字段。</p>
                  </article>
                </div>
                {showClassificationDetails ? (
                  <div className="evidencePanel">
                    <div className="sectionHeader">
                      <h3>M1/M2 分析依据</h3>
                      <span className="badge">classification_detail</span>
                    </div>
                    <div className="resultGrid">
                      <article className="resultCard">
                        <span>识别到的项目类型</span>
                        <strong>{labelForProjectType(classification.detected_project_type)}</strong>
                        <p>project_type：{classification.detected_project_type ?? "待识别"}</p>
                      </article>
                      <article className="resultCard">
                        <span>对应 PPT 模板</span>
                        <strong>{firstTemplateName(classification.template_selection?.M1_M2)}</strong>
                        <p>只选择既有 M1/M2 固化模板，不动态生成整章内容。</p>
                      </article>
                      <article className="resultCard">
                        <span>confidence</span>
                        <strong>{classification.confidence ? `${Math.round(classification.confidence * 100)}%` : "待识别"}</strong>
                        <p>供前端人工确认时参考。</p>
                      </article>
                      <article className="resultCard">
                        <span>matched_keywords</span>
                        <strong>{classification.matched_keywords?.join("、") || "待识别"}</strong>
                        <p>命中关键词来自项目名称、文件名和解析文本。</p>
                      </article>
                      <article className="resultCard">
                        <span>分类方式</span>
                        <strong>{classification.classification_method === "llm" ? "LLM" : classification.classification_method === "rule_fallback" ? "规则 fallback" : "待识别"}</strong>
                        <p>{classification.fallback_reason || "LLM 可用时优先使用模板画像判断。"}</p>
                      </article>
                      <article className="resultCard">
                        <span>LLM 判断理由</span>
                        <strong>{classification.llm_reasoning_summary || "暂无"}</strong>
                        <p>模型只判断模板类型，不动态生成 M1/M2 内容。</p>
                      </article>
                    </div>
                    <div className="sectionHeader">
                      <h3>判断依据</h3>
                      <span className="badge">detection_evidence</span>
                    </div>
                    {classification.detection_evidence?.length ? (
                      <div className="evidenceList">
                        {classification.detection_evidence.map((item, index) => (
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
                ) : null}
                {productLineClassificationConflict ? (
                  <p className="messageLine">
                    新建项目选择的产品线"{productLineClassificationConflict.productLine}"对应{labelForProjectType(productLineClassificationConflict.preferredProjectType)}，资料识别结果为{labelForProjectType(productLineClassificationConflict.detectedProjectType)}。已默认按产品线选择 M1/M2；如资料判断更准确，请在下方人工确认中修改。
                  </p>
                ) : null}
                <form className="confirmationGrid" onSubmit={(event) => { event.preventDefault(); submitClassificationReview(); }}>
                  <label>确认项目类型<select aria-label="确认项目类型" value={reviewForm.projectType} onChange={(event) => { const nextType = event.target.value; setReviewForm((value) => ({ ...value, projectType: nextType, m1m2Template: nextType })); }}>{projectTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                  <label>确认 M1/M2 模板<select aria-label="确认 M1/M2 模板" value={reviewForm.m1m2Template} onChange={(event) => { const nextType = event.target.value; setReviewForm((value) => ({ ...value, projectType: nextType, m1m2Template: nextType })); }}>{m1m2Templates.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                  <label>确认 M3 模块<select aria-label="确认 M3 模块" value={reviewForm.m3Selection} onChange={(event) => setReviewForm((value) => ({ ...value, m3Selection: event.target.value }))}><option value="m3_template">M3模板</option><option value="m3_skip">暂不选择</option></select></label>
                  <label>确认 M5 案例<select aria-label="确认 M5 案例" value={reviewForm.caseId ?? ""} onChange={(event) => setReviewForm((value) => ({ ...value, caseId: event.target.value }))}>{recommendedCases[0] ? <option value={String(recommendedCases[0].case_id)}>{recommendedCases[0].title || recommendedCases[0].case_id}</option> : null}{m5FixedCases.filter((item) => String(item.case_id) !== String(recommendedCases[0]?.case_id)).map((item) => <option key={item.case_id} value={item.case_id}>{item.filename || item.title}</option>)}<option value="">暂不选择案例</option></select></label>
                  <label className="checkboxField"><input checked={reviewForm.includePrintTailPage} onChange={(event) => setReviewForm((value) => ({ ...value, includePrintTailPage: event.target.checked }))} type="checkbox" />添加尾页打印版</label>
                  <button className="primaryButton" disabled={busy} type="submit">提交人工确认</button>
                </form>
              </>
            ) : (
              <div className="emptyState compact"><h3>等待系统识别</h3><p>统一上传项目资料后，点击开始识别资料，即可在此确认项目类型、模板选择、案例选择和缺失字段。</p></div>
            )}
          </section>

          <section className="section statusSection">
            <div className="sectionHeader"><h2>生成状态</h2><div className="actions"><button className="primaryButton btn-xs" disabled={busy} onClick={generate} type="button">启动生成</button></div></div>
            <ol className="statusList">{["待上传", "资料解析中", "类型识别中", "案例匹配中", "待确认", "生成中", "合并中", "完成"].map((status, index) => <li className={status === activeStatus ? "current" : (["待上传", "资料解析中", "类型识别中", "案例匹配中", "待确认", "生成中", "合并中", "完成"].indexOf(status) < ["待上传", "资料解析中", "类型识别中", "案例匹配中", "待确认", "生成中", "合并中", "完成"].indexOf(activeStatus) ? "completed" : "pending")} key={status}><span>{index + 1}</span>{status}</li>)}</ol>
            <div className="historyBox"><strong>状态历史</strong><span>{statusHistory}</span></div>
            <p className="messageLine">{message}</p>
            {qualityReport ? (
              <div className="evidencePanel spaced qualityReportPanel">
                <button
                  aria-expanded={qualityReportExpanded}
                  className="qualityReportSummary"
                  onClick={() => setQualityReportExpanded(!qualityReportExpanded)}
                  type="button"
                >
                  <span className="qualityReportTitle">
                    <strong>质量检查结果</strong>
                    <span className="badge">QAReviewAgent</span>
                  </span>
                  <span className="qualityReportMeta">
                    <strong>{qualityReportLabel(qualityReport)}</strong>
                    <span>{qualityReport.errors?.length ?? 0} 错误 / {qualityReport.warnings?.length ?? 0} 风险</span>
                  </span>
                  <span className="qualityReportToggle">{qualityReportExpanded ? "收起" : "展开详情"}</span>
                </button>
                {qualityReportExpanded ? (
                  <div className="qualityReportDetails">
                    <div className="qualityReportActions">
                      <button className="secondaryButton btn-xs" onClick={() => setQualityReportExpanded(false)} type="button">收起</button>
                    </div>
                    <div className="resultGrid">
                      <article className="resultCard">
                        <span>检查状态</span>
                        <strong>{qualityReportLabel(qualityReport)}</strong>
                        <p>第一版 QAReviewAgent 只做结果提示，不影响下载。</p>
                      </article>
                      <article className="resultCard">
                        <span>检查时间</span>
                        <strong>{qualityReport.checked_at || "未返回"}</strong>
                        <p>passed：{String(Boolean(qualityReport.passed))}；severity：{qualityReport.severity || "unknown"}</p>
                      </article>
                      <article className="resultCard">
                        <span>errors</span>
                        <strong>{qualityReport.errors?.length ?? 0} 项</strong>
                        <p>{(qualityReport.errors ?? []).slice(0, 3).join("；") || "未发现阻断级错误。"}</p>
                      </article>
                      <article className="resultCard">
                        <span>warnings</span>
                        <strong>{qualityReport.warnings?.length ?? 0} 项</strong>
                        <p>{(qualityReport.warnings ?? []).slice(0, 3).join("；") || "未发现提示级风险。"}</p>
                      </article>
                    </div>
                    <div className="qualityReportActions bottom">
                      <button className="secondaryButton btn-xs" onClick={() => setQualityReportExpanded(false)} type="button">收起</button>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
            <div className="downloadRow"><div><h3>最终文件</h3><p id="finalFileDesc">生成完成后可下载、预览或存入完整PPT案例库</p></div><div className="downloadActions"><button className="secondaryButton btn-xs" disabled={busy || !canSaveFullPptCase} onClick={saveFullPptCase} type="button">存入案例库</button><button className="secondaryButton btn-xs" disabled={busy || previewLoading} onClick={previewFinalPpt} type="button">{previewLoading ? "生成预览中..." : "预览 PPT"}</button><button className="secondaryButton btn-xs" disabled={busy} onClick={downloadFinal} type="button">下载最终 PPTX</button><span className="badge">{activeStatus}</span></div></div>
          </section>
        </>
      ) : null}
    </>
  );
}
