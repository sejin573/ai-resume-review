import AppShell from "./AppShell";

export default function Layout({ title, subtitle, children }) {
  return (
    <AppShell title={title} subtitle={subtitle}>
      {children}
    </AppShell>
  );
}
