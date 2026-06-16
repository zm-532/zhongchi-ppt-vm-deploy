interface CreateProjectViewProps {
  busy: boolean;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
}

export function CreateProjectView({ busy, onSubmit }: CreateProjectViewProps) {
  return (
    <section id="create" className="section">
      <div className="sectionHeader"><h2>新建项目</h2><span className="badge">基础信息</span></div>
      <form className="projectForm" onSubmit={onSubmit}>
        <label>项目名称*<input name="project_name" placeholder="例如：某城市轨道交通声屏障改造项目" /></label>
        <label>项目所在地*<input name="project_location" placeholder="例如：南京" /></label>
        <label>建设/业主单位*<input name="owner_unit" placeholder="例如：某建设单位" /></label>
        <label>产品线*<select aria-label="产品线" name="product_line" defaultValue="">
          <option value="">请选择产品线</option>
          <option value="轨道交通声屏障">轨道交通声屏障</option>
          <option value="轨交既有线改造">轨交既有线改造</option>
          <option value="公路声屏障">公路声屏障</option>
          <option value="铁路声屏障">铁路声屏障</option>
        </select></label>
        <button className="primaryButton" disabled={busy} type="submit">创建项目</button>
      </form>
    </section>
  );
}
