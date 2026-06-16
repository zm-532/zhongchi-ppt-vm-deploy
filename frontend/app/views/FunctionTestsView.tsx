export function FunctionTestsView() {
  return (
    <section id="function-tests" className="section">
      <div className="sectionHeader">
        <h2>功能测试</h2>
        <span className="badge">开发过程验证入口</span>
      </div>
      <div className="test-hub-grid">
        <article className="test-hub-card">
          <div className="test-hub-card-header">
            <strong>M1/M2选择测试</strong>
            <span className="test-hub-badge">模板识别</span>
          </div>
          <p className="test-hub-desc">验证项目类型识别与 M1/M2 固化模板选择。</p>
          <a className="secondaryButton test-hub-action" href="#m1m2-test">打开测试</a>
        </article>
        <article className="test-hub-card">
          <div className="test-hub-card-header">
            <strong>M3完整测试</strong>
            <span className="test-hub-badge">M3完整</span>
          </div>
          <p className="test-hub-desc">按九个部分测试 M3 文字与图片替换，多图自动扩页。</p>
          <a className="secondaryButton test-hub-action" href="#m3-full-test">打开测试</a>
        </article>
        <article className="test-hub-card">
          <div className="test-hub-card-header">
            <strong>M5选择测试</strong>
            <span className="test-hub-badge">案例匹配</span>
          </div>
          <p className="test-hub-desc">验证项目标签、案例库匹配与推荐理由。</p>
          <a className="secondaryButton test-hub-action" href="#m5-test">打开测试</a>
        </article>
        <article className="test-hub-card">
          <div className="test-hub-card-header">
            <strong>文档解析测试</strong>
            <span className="test-hub-badge">解析验证</span>
          </div>
          <p className="test-hub-desc">验证上传资料解析状态、资料角色和模块分配。</p>
          <a className="secondaryButton test-hub-action" href="#document-parse-test">打开测试</a>
        </article>
        <article className="test-hub-card">
          <div className="test-hub-card-header">
            <strong>大模型测试</strong>
            <span className="test-hub-badge">LLM</span>
          </div>
          <p className="test-hub-desc">通过后端读取环境变量并调用配置好的接口。</p>
          <a className="secondaryButton test-hub-action" href="#llm-test">打开测试</a>
        </article>
      </div>
    </section>
  );
}
