import "./globals.css";

export const metadata = {
  title: "ILMCS — Industrial Land Monitoring & Compliance System",
  description:
    "Satellite-based monitoring of industrial land allotments in Chhattisgarh using Sentinel-2 + ESRGAN AI super-resolution",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark h-full">
      <head>
        <link
          href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full">{children}</body>
    </html>
  );
}
