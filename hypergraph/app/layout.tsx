import type { Metadata } from "next";
import { Manrope, DM_Sans, Geist_Mono } from "next/font/google";
import "./globals.css";
import Script from "next/script";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HyperGraph",
  description: "Give your agent a domain to understand, not just instructions to follow.",
  icons: {
    icon: "/hb-symbol.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var stored = localStorage.getItem("hypergraph-theme");
                  var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
                  var theme = stored === "light" || stored === "dark" ? stored : (prefersDark ? "dark" : "light");
                  document.documentElement.setAttribute("data-theme", theme);
                } catch (_) {
                  document.documentElement.setAttribute("data-theme", "light");
                }
              })();
            `,
          }}
        />
        {process.env.NODE_ENV === "development" && (
          <Script
            src="//unpkg.com/react-grab/dist/index.global.js"
            crossOrigin="anonymous"
            strategy="beforeInteractive"
          />
        )}
      </head>
      <body
        className={`${manrope.variable} ${dmSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
