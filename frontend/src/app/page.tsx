import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-black text-white overflow-hidden">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 px-6 py-4 flex items-center justify-between border-b border-white/10 bg-black/80 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <span className="font-bold text-lg tracking-tight">TradeDash</span>
        </div>
        <div className="hidden md:flex items-center gap-6 text-sm text-white/60">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm" className="text-white/80 hover:text-white hover:bg-white/10">
              Sign In
            </Button>
          </Link>
          <Link href="/signup">
            <Button size="sm" className="bg-primary hover:bg-primary/90 rounded-full px-5">
              Get Started
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-36 pb-24 px-6 text-center relative">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: "radial-gradient(ellipse 60% 40% at 50% 0%, rgba(0,113,227,0.12), transparent)",
          }}
        />
        <Badge className="mb-8 bg-primary/10 text-primary border-primary/20 text-xs uppercase tracking-widest px-4 py-1.5">
          NSE · Live Data
        </Badge>
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05] mb-6 max-w-4xl mx-auto">
          Professional Trading
          <br />
          <span className="text-primary">Analytics</span>
        </h1>
        <p className="text-lg md:text-xl text-white/55 max-w-2xl mx-auto mb-12 leading-relaxed">
          Real-time buy/sell signals, live options chain, and ML-powered direction
          predictions for NIFTY 50 stocks.
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <Link href="/signup">
            <Button
              size="lg"
              className="bg-primary hover:bg-primary/90 text-white h-12 px-8 rounded-full text-base font-medium"
            >
              Get Started Free
            </Button>
          </Link>
          <Link href="/login">
            <Button
              size="lg"
              variant="outline"
              className="border-white/20 text-white hover:bg-white/5 h-12 px-8 rounded-full text-base"
            >
              Sign In
            </Button>
          </Link>
        </div>
      </section>

      {/* Feature cards */}
      <section id="features" className="py-20 px-6 max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 text-white/90">
          Everything you need to trade smarter
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              title: "Live Signals",
              desc: "BUY / SELL / HOLD with confidence scores from 6 technical indicators — RSI, MACD, EMA, Bollinger, S/R, OBV.",
              accent: "text-green-400",
              dot: "bg-green-400",
            },
            {
              title: "Options Chain",
              desc: "Real-time OI data for NIFTY, BANKNIFTY, MIDCPNIFTY. PCR, Max Pain, and curated trade recommendations.",
              accent: "text-blue-400",
              dot: "bg-blue-400",
            },
            {
              title: "ML Predictions",
              desc: "Random Forest model trained on 12 technical features. Direction probability updated hourly.",
              accent: "text-orange-400",
              dot: "bg-orange-400",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="glass rounded-2xl p-8 transition-all duration-300 hover:scale-[1.01]"
            >
              <div className={`w-2 h-2 rounded-full ${f.dot} mb-4`} />
              <h3 className={`text-xl font-bold mb-3 ${f.accent}`}>{f.title}</h3>
              <p className="text-white/55 leading-relaxed text-sm">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing — free beta */}
      <section id="pricing" className="py-20 px-6 text-center max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-5xl font-bold mb-4 text-white/90">
          Free During Beta
        </h2>
        <p className="text-white/50 mb-12 text-lg">
          All features are available at no cost while we&apos;re in beta. No credit card required.
        </p>
        <div className="glass rounded-2xl p-10 text-left relative overflow-hidden">
          <div className="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none" />
          <Badge className="mb-6 bg-green-500/10 text-green-400 border-green-500/20 text-xs uppercase tracking-widest px-3 py-1">
            Beta Access
          </Badge>
          <div className="text-6xl font-bold mb-2 text-white">
            ₹0
            <span className="text-2xl text-white/35 font-normal ml-1">/ forever (for now)</span>
          </div>
          <p className="text-white/55 text-sm mb-8 max-w-sm">
            Sign up and get full access to live options chain, OI analytics, ML predictions,
            and the Nifty 50 scanner — completely free.
          </p>
          <Link href="/signup">
            <Button
              size="lg"
              className="bg-primary hover:bg-primary/90 text-white h-12 px-8 rounded-full text-base font-medium"
            >
              Get Started Free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8 px-6 text-center text-white/30 text-sm">
        © 2026 TradeDash. For informational purposes only. Not financial advice.
      </footer>
    </main>
  );
}
