export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-16">
      <div className="rounded-2xl border bg-white p-8">
        <h1 className="text-3xl font-semibold tracking-tight">Natiah</h1>
        <p className="mt-3 text-zinc-600">
          Full-stack LinkedIn outreach automation SaaS boilerplate.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <a
            href="/login"
            className="inline-flex items-center justify-center rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white"
          >
            Login
          </a>
          <a
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-xl border px-4 py-2 text-sm font-medium"
          >
            Dashboard
          </a>
        </div>
      </div>
    </main>
  );
}
