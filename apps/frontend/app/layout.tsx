import './globals.css';
import type { ReactNode } from 'react';
import AppShell from '../components/app-shell';

export const metadata = {
  title: 'Rockstream Transcode Portal',
  description: 'Transcode and streaming control portal powered by GStreamer',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
