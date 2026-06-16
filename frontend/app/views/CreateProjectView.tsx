"use client";

import { useState } from "react";

interface CreateProjectViewProps {
  busy: boolean;
  onSubmit: (event: React.FormEvent<HTMLFormElement>, isValid: boolean) => void;
}

export function CreateProjectView({ busy, onSubmit }: CreateProjectViewProps) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  function validateField(name: string, value: string): string {
    if (name === "project_name" && !value.trim()) return "项目名称不能为空";
    if (name === "product_line" && !value) return "请选择产品线";
    return "";
  }

  function handleBlur(e: React.FocusEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = e.target;
    setTouched((prev) => ({ ...prev, [name]: true }));
    const error = validateField(name, value);
    setErrors((prev) => ({ ...prev, [name]: error }));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const newErrors: Record<string, string> = {};
    const newTouched: Record<string, boolean> = {};

    for (const name of ["project_name", "product_line"]) {
      const value = String(formData.get(name) || "");
      newTouched[name] = true;
      newErrors[name] = validateField(name, value);
    }

    setTouched(newTouched);
    setErrors(newErrors);

    const hasErrors = Object.values(newErrors).some(Boolean);
    if (!hasErrors) {
      onSubmit(event, true);
    }
  }

  function fieldClassName(name: string) {
    return touched[name] && errors[name] ? "input-error" : "";
  }

  return (
    <section id="create" className="section">
      <div className="sectionHeader"><h2>新建项目</h2><span className="badge">基础信息</span></div>
      <form className="projectForm" onSubmit={handleSubmit} noValidate>
        <label>
          项目名称*
          <input
            name="project_name"
            placeholder="例如：某城市轨道交通声屏障改造项目"
            className={fieldClassName("project_name")}
            onBlur={handleBlur}
          />
          {touched.project_name && errors.project_name ? <span className="field-error">{errors.project_name}</span> : null}
        </label>
        <label>
          项目所在地
          <input name="project_location" placeholder="例如：南京" />
        </label>
        <label>
          建设/业主单位
          <input name="owner_unit" placeholder="例如：某建设单位" />
        </label>
        <label>
          产品线*
          <select
            aria-label="产品线"
            name="product_line"
            defaultValue=""
            className={fieldClassName("product_line")}
            onBlur={handleBlur}
          >
            <option value="" disabled>请选择产品线</option>
            <option value="轨道交通声屏障">轨道交通声屏障</option>
            <option value="轨交既有线改造">轨交既有线改造</option>
            <option value="公路声屏障">公路声屏障</option>
            <option value="铁路声屏障">铁路声屏障</option>
          </select>
          {touched.product_line && errors.product_line ? <span className="field-error">{errors.product_line}</span> : null}
        </label>
        <button className="primaryButton" disabled={busy} type="submit">创建项目</button>
      </form>
    </section>
  );
}
