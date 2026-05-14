import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "中驰售前PPT助手",
  description: "按模块上传材料并生成中驰解决方案PPT初稿",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
