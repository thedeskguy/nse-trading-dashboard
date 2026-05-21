interface PaywallGateProps {
  feature?: string;
  children: React.ReactNode;
}

// Free beta launch: gate is bypassed — all features available to all users.
// Re-wire useSubscription check here when payments are re-enabled.
export function PaywallGate({ children }: PaywallGateProps) {
  return <>{children}</>;
}
