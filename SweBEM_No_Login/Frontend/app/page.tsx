"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Demo build: no authentication, go straight to the simulator.
    router.push('/simulator');
  }, [router]);

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
    </main>
  );
}
