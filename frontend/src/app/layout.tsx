import './globals.css';
import AdminShell from '@/components/AdminShell';

export const metadata = {
  title: 'NTC Anonymous Detection & Recognition',
  description: 'NTC admin dashboard for anonymous detection and recognition',
  icons: {
    icon: '/ntc-logo.png',
    shortcut: '/ntc-logo.png',
    apple: '/ntc-logo.png',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <AdminShell>{children}</AdminShell>
      </body>
    </html>
  );
}
