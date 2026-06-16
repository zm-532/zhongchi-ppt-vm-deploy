import { M3_FULL_SECTIONS } from "../constants";

export function M3NamingHelpModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="modalBackdrop" role="presentation" onMouseDown={onClose}>
      <div aria-modal="true" className="modalPanel" role="dialog" onMouseDown={(event) => event.stopPropagation()}>
        <div className="modalHeader">
          <h2>M3图片命名规则</h2>
          <button aria-label="关闭命名规则弹窗" className="iconCloseButton" onClick={onClose} type="button">×</button>
        </div>
        <div className="namingRules">
          <p>总共有这九类：</p>
          <div className="ruleGrid">
            {M3_FULL_SECTIONS.map((section) => <span key={`rule-${section.imageField}`}>{section.title}</span>)}
          </div>
          <p>如果只有一张图，可以使用“项目基本情况.jpg”。</p>
          <p>多张图必须使用“项目基本情况-1.jpg”“项目基本情况-2.jpg”。</p>
          <p>描述文本按同样编号填写，例如“项目基本情况-1：第一张图片说明”。</p>
        </div>
      </div>
    </div>
  );
}
