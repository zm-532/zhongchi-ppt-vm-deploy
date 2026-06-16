import type { LlmTestResult } from "../constants";

interface LlmTestViewProps {
  llmTestPrompt: string;
  setLlmTestPrompt: (value: string) => void;
  llmTestMessage: string;
  llmTestResult: LlmTestResult | null;
  busy: boolean;
  runLlmConnectionTest: () => void;
}

export function LlmTestView({ llmTestPrompt, setLlmTestPrompt, llmTestMessage, llmTestResult, busy, runLlmConnectionTest }: LlmTestViewProps) {
  return (
    <section id="llm-test" className="section">
      <div className="sectionHeader">
        <h2>大模型测试</h2>
        <span className="badge">页面调用验证</span>
      </div>
      <div className="testPanel">
        <label>
          测试提示词
          <textarea
            value={llmTestPrompt}
            onChange={(event) => setLlmTestPrompt(event.target.value)}
            rows={4}
          />
        </label>
        <button className="primaryButton" disabled={busy} onClick={runLlmConnectionTest} type="button">调用大模型测试</button>
        <p className="messageLine">{llmTestMessage}</p>
      </div>

      {llmTestResult ? (
        <div className="resultGrid">
          <article className="resultCard">
            <span>调用状态</span>
            <strong>{llmTestResult.ok ? "成功" : "失败"}</strong>
            <p>HTTP status：{llmTestResult.status_code || "无响应"}</p>
          </article>
          <article className="resultCard">
            <span>模型</span>
            <strong>{llmTestResult.model || "未返回"}</strong>
            <p>由后端读取 ZHONGCHI_LLM_MODEL。</p>
          </article>
          <article className="resultCard wide">
            <span>模型回复</span>
            <strong>{llmTestResult.reply || "无回复"}</strong>
            <p>{llmTestResult.error ? `错误信息：${llmTestResult.error}` : "后端不会向前端返回 API Key。"}</p>
          </article>
          <article className="resultCard">
            <span>配置检查</span>
            <strong>{llmTestResult.configured?.base_url && llmTestResult.configured?.api_key && llmTestResult.configured?.model ? "完整" : "缺失"}</strong>
            <p>base_url：{String(Boolean(llmTestResult.configured?.base_url))}；api_key：{String(Boolean(llmTestResult.configured?.api_key))}；model：{String(Boolean(llmTestResult.configured?.model))}</p>
          </article>
        </div>
      ) : null}
    </section>
  );
}
