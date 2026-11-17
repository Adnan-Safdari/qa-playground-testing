import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/lib/theme-provider";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: {
    default: "SecureBank",
    template: "%s | SecureBank",
  },
  description:
    "SecureBank — demo banking application used as the system under test for BankTest automated regression testing.",
  robots: "noindex, nofollow",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} disableTransitionOnChange>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
