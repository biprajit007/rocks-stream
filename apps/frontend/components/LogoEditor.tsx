'use client';

import { useState } from 'react';

export default function LogoEditor({ x, y, width, height, onChange, onSizeChange }: { x: number; y: number; width: number; height: number; onChange: (x: number, y: number) => void; onSizeChange: (width: number, height: number) => void }) {
  const [dragging, setDragging] = useState(false);
  const ratio = Math.max(0.1, height / Math.max(1, width));

  function resize(nextWidth: number) {
    const safeWidth = Math.max(36, Math.min(320, nextWidth));
    onSizeChange(safeWidth, Math.max(18, Math.round(safeWidth * ratio)));
  }

  return (
    <div>
      <div
        className="preview-stage preview-stage-small"
        onMouseMove={(event) => {
          if (!dragging) return;
          const rect = (event.currentTarget as HTMLDivElement).getBoundingClientRect();
          onChange(Math.max(0, Math.round(event.clientX - rect.left)), Math.max(0, Math.round(event.clientY - rect.top)));
        }}
        onMouseUp={() => setDragging(false)}
        onMouseLeave={() => setDragging(false)}
        onWheel={(event) => {
          event.preventDefault();
          const delta = event.deltaY > 0 ? -8 : 8;
          resize(width + delta);
        }}
      >
        <div className="logo-node" onMouseDown={() => setDragging(true)} style={{ left: x, top: y, width, height }}>
          Drag logo
        </div>
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <span className="muted">x: {x}</span>
        <span className="muted">y: {y}</span>
        <span className="muted">size: {width} × {height}</span>
        <button className="secondary" type="button" onClick={() => resize(width - 12)}>Smaller</button>
        <button className="secondary" type="button" onClick={() => resize(width + 12)}>Bigger</button>
      </div>
      <div className="muted tiny" style={{ marginTop: 6 }}>Tip: use mouse wheel on the editor to resize the logo.</div>
    </div>
  );
}
