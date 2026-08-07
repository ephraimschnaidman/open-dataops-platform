import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "Dashboard · Datum",
    description: "Modern data operations platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
