import { redirect } from "next/navigation";

// Stocks listing merged into the Dashboard page.
export default function StocksPage() {
  redirect("/dashboard");
}
