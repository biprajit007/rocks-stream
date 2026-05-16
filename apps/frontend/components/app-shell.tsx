'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';
import ThemeToggle from './theme-toggle';

const navGroups = [
  {
    label: 'Live',
    items: [
      { href: '/dashboard#live-realtime', label: 'Overview' },
      { href: '/dashboard#monitoring', label: 'Streams' },
      { href: '/dashboard#manage-data-slices', label: 'Inspector' },
      { href: '/dashboard#manage-playback', label: 'Details' },
    ],
  },
  {
    label: 'Create',
    items: [
      { href: '/dashboard#live-streams', label: 'New stream' },
      { href: '/dashboard#live-inputs', label: 'Inputs' },
      { href: '/dashboard#live-outputs', label: 'Outputs' },
      { href: '/dashboard#live-abr', label: 'ABR' },
    ],
  },
  {
    label: 'Ads',
    items: [
      { href: '/ads', label: 'Ad manager' },
    ],
  },
  {
    label: 'Social',
    items: [
      { href: '/social', label: 'Social stream' },
    ],
  },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLogin = pathname === '/login';

  if (isLogin) {
    return <main className="login-shell">{children}</main>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">RS</div>
          <div>
            <div className="brand-name">Rockstream</div>
            <div className="muted tiny">Transcode Portal</div>
          </div>
        </div>
        <div className="menu-stack">
          {navGroups.map((group) => (
            <div key={group.label} className="menu-group">
              <div className="menu-group-title">{group.label}</div>
              {group.items.map((item) => (
                <Link key={item.href} className="menu-subitem" href={item.href}>
                  {item.label}
                </Link>
              ))}
            </div>
          ))}
        </div>
        <div className="sidebar-footer">
          <div className="muted tiny">Managed streaming control plane</div>
        </div>
      </aside>
      <main className="content-shell">
        <header className="page-header">
          <div>
            <div className="eyebrow">Rockstream</div>
            <h1>Transcode Portal</h1>
          </div>
          <div className="row">
            <ThemeToggle />
            <Link className="secondary" href="/dashboard">Dashboard</Link>
            <Link className="secondary" href="/ads">Ads</Link>
            <Link className="secondary" href="/social">Social</Link>
          </div>
        </header>
        <section className="content-area">{children}</section>
      </main>
    </div>
  );
}
