'use client';

import { useState } from 'react';

export default function LogoEditor({ x, y, onChange }: { x: number; y: number; onChange: (x: number, y: number) => void }) {
  const [dragging, setDragging] = useState(false);

  return (
    <div>
      <div
        className="preview-stage"
        onMouseMove={(event) => {
          if (!dragging) return;
          const rect = (event.currentTarget as HTMLDivElement).getBoundingClientRect();
          onChange(Math.max(0, Math.round(event.clientX - rect.left)), Math.max(0, Math.round(event.clientY - rect.top)));
        }}
        onMouseUp={() => setDragging(false)}
        onMouseLeave={() => setDragging(false)}
      >
        <div className="logo-node" onMouseDown={() => setDragging(true)} style={{ left: x, top: y }}>
          Drag logo
        </div>
      </div>
      <div className="row" style={{ marginTop: 8 }}>
        <span className="muted">x: {x}</span>
        <span className="muted">y: {y}</span>
      </div>
    </div>
  );
}
