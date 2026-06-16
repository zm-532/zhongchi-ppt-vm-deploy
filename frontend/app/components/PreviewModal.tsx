import { API_BASE } from "../constants";
import type { Project } from "../constants";
import { useState } from "react";

interface PreviewModalProps {
  slides: { index: number; image_url: string }[];
  currentIndex: number;
  onIndexChange: (index: number) => void;
  onClose: () => void;
  error: string;
  currentProject: Project | null;
}

export function PreviewModal({ slides, currentIndex, onIndexChange, onClose, error, currentProject }: PreviewModalProps) {
  const [jumpPage, setJumpPage] = useState("");

  function handleJump(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && jumpPage.trim()) {
      const page = parseInt(jumpPage, 10);
      if (page >= 1 && page <= slides.length) {
        onIndexChange(page - 1);
        setJumpPage("");
      }
    }
  }

  return (
    <div className="modalBackdrop" role="presentation" onMouseDown={onClose}>
      <div aria-modal="true" className="previewModalPanel" role="dialog" onMouseDown={(event) => event.stopPropagation()}>
        <div className="modalHeader">
          <h2>PPT 预览 ({currentIndex + 1} / {slides.length})</h2>
          <button aria-label="关闭预览" className="iconCloseButton" onClick={onClose} type="button">&times;</button>
        </div>
        {error ? <div className="previewError">{error}</div> : null}
        <div className="previewBody">
          <button
            className="previewNavButton"
            disabled={currentIndex <= 0}
            onClick={() => onIndexChange(Math.max(0, currentIndex - 1))}
            type="button"
          >&lsaquo;</button>
          <div className="previewImageContainer">
            {slides.length > 0 ? (
              <img
                className="previewImage"
                src={`${API_BASE}${slides[currentIndex].image_url}`}
                alt={`第 ${currentIndex + 1} 页`}
              />
            ) : null}
          </div>
          <button
            className="previewNavButton"
            disabled={currentIndex >= slides.length - 1}
            onClick={() => onIndexChange(Math.min(slides.length - 1, currentIndex + 1))}
            type="button"
          >&rsaquo;</button>
        </div>
        <div className="previewThumbnailStrip">
          {slides.map((slide, idx) => (
            <button
              key={slide.index}
              className={`previewThumbnail${idx === currentIndex ? " previewThumbnailActive" : ""}`}
              onClick={() => onIndexChange(idx)}
              type="button"
            >
              <img src={`${API_BASE}${slide.image_url}`} alt={`缩略图 ${slide.index}`} />
              <span>{slide.index}</span>
            </button>
          ))}
          {slides.length > 5 ? (
            <div className="previewPageJump">
              <span>跳转</span>
              <input
                className="previewPageInput"
                type="number"
                min={1}
                max={slides.length}
                value={jumpPage}
                onChange={(e) => setJumpPage(e.target.value)}
                onKeyDown={handleJump}
                placeholder="#"
              />
              <span>/ {slides.length} 页</span>
            </div>
          ) : null}
        </div>
        <div className="previewFooter">
          <a className="primaryButton btn-xs" href={`${API_BASE}/api/projects/${currentProject?.project_id}/download`} download>下载 PPTX</a>
        </div>
      </div>
    </div>
  );
}
