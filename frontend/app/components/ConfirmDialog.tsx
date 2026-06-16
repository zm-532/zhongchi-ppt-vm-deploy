import { useEffect, useRef } from "react";

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  message,
  confirmText = "确认",
  cancelText = "取消",
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  useEffect(() => {
    panelRef.current?.focus();
  }, []);

  return (
    <div className="modalBackdrop" role="presentation" onMouseDown={onCancel}>
      <div
        ref={panelRef}
        className="confirmDialogPanel"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        tabIndex={-1}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="confirmDialogHeader">
          <h3 id="confirm-dialog-title">{title}</h3>
        </div>
        <div className="confirmDialogBody">
          <p>{message}</p>
        </div>
        <div className="confirmDialogActions">
          <button className="secondaryButton" onClick={onCancel} type="button">
            {cancelText}
          </button>
          <button
            className={danger ? "dangerButton" : "primaryButton"}
            onClick={onConfirm}
            type="button"
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
