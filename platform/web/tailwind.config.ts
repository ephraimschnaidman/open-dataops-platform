import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            boxShadow: {
                card: "0 1px 2px rgba(15, 23, 42, 0.04)",
                panel: "0 18px 50px rgba(15, 23, 42, 0.15)",
            },
        },
    },
    plugins: [],
};

export default config;
