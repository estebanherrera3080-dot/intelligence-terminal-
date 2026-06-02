import dynamic from "next/dynamic";

// ssr: false eliminates all hydration mismatches —
// the dashboard renders purely client-side after mount.
const Dashboard = dynamic(() => import("./dashboard"), { ssr: false });

export default function Page() {
  return <Dashboard />;
}
