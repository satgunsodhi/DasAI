import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DasAI Admin Console",
  description: "Admin dashboard for the Discord Copilot bot",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
