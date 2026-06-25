import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Buttery — native-speaker rating",
  description: "Rate machine-generated Indic-language tasks for a research dataset.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
