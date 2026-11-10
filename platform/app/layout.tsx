import type { Metadata } from 'next';
import './globals.css';
import './dark.css';
export const metadata: Metadata = {title:'Kairo — Japan Power Observatory',description:'A Japanese and English workspace for JEPX day-ahead forecasts, honest model evaluation, and traceable market data.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
