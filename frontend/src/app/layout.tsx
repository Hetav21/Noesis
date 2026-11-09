import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Noesis",
  description: "Autonomous multi-agent research and synthesis engine.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col selection:bg-zinc-700 selection:text-white">
        <Navbar />
        <main className="flex-1 flex flex-col">{children}</main>
        <footer className="border-t border-white/[0.06] py-6 px-4 text-xs text-zinc-500">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <span className="font-mono text-zinc-400">Noesis</span>
            <span className="text-zinc-500">
              Made with care by{" "}
              <a
                href="https://hetav.dev"
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-300 hover:text-white underline underline-offset-4 decoration-zinc-600 hover:decoration-zinc-300 transition-colors"
              >
                hetav.dev
              </a>
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
