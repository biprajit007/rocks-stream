import './globals.css';
import Link from 'next/link';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'Rocks Stream',
  description: 'Streaming control plane powered by GStreamer'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <div className="topbar">
            <div>
              <div className="muted">Rocks Stream</div>
              <h1 style={{ margin: 0 }}>Streaming control plane</h1>
            </div>
            <div className="row">
              <Link href="/dashboard">Dashboard</Link>
              <Link href="/login">Login</Link>
            </div>
          </div>
          {children}
        </div>
      </body>
    </html>
  );
}
