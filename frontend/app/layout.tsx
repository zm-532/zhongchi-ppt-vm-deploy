import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "中驰售前PPT助手",
  description: "统一上传项目资料并生成中驰解决方案PPT初稿",
  icons: {
    icon: "/brand-icon.png",
    shortcut: "/brand-icon.png",
    apple: "/brand-icon.png",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
