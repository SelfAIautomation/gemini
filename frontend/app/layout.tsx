import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'CB Terminal',
  description: '仮想通貨・マクロ経済ニュース端末',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>{`
          *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
          html, body { height: 100%; }
          body {
            background: #0a0a0a;
            color: #e8e8e8;
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.5;
            overflow: hidden;
          }
          ::-webkit-scrollbar { width: 4px; }
          ::-webkit-scrollbar-track { background: #111; }
          ::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }
          a { color: inherit; text-decoration: none; }
          button { font-family: inherit; }
        `}</style>
      </head>
      <body>{children}</body>
    </html>
  )
}
