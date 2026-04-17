import { ScanSearch } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function ScannerPage() {
  return (
    <div className="space-y-4 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Scanner</h1>
        <p className="text-muted-foreground text-sm mt-1">Nifty 100 batch signal scanner</p>
      </div>
      <div className="bg-card border border-border rounded-2xl py-20 flex flex-col items-center gap-4 text-center">
        <ScanSearch size={40} className="text-muted-foreground/25" />
        <div>
          <p className="text-muted-foreground text-sm font-medium">Multi-stock signal scanner</p>
          <p className="text-muted-foreground/60 text-xs mt-1">Scan all Nifty 100 stocks for BUY / SELL signals in one view</p>
        </div>
        <Badge variant="outline" className="text-xs text-muted-foreground border-border">
          Coming in Phase 8
        </Badge>
      </div>
    </div>
  );
}
