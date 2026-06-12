import { Info } from "lucide-react";

interface Props {
  title?: string;
  children: React.ReactNode;
}

export function MethodologyNote({ title = "How this is computed", children }: Props) {
  return (
    <details className="bg-muted/30 border border-border rounded-xl px-4 py-3 text-xs text-muted-foreground">
      <summary className="cursor-pointer select-none font-medium text-foreground/70 hover:text-foreground transition-colors inline-flex items-center gap-1.5">
        <Info size={12} className="shrink-0" />
        {title}
      </summary>
      <div className="mt-2 leading-relaxed space-y-1.5">{children}</div>
    </details>
  );
}
