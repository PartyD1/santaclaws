import { ClawDetail } from "@/components/ClawDetail";
import type { ClawName } from "@/lib/types";

type ClawDetailPageProps = {
  params: {
    name: ClawName;
  };
};

export default function ClawDetailPage({ params }: ClawDetailPageProps) {
  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <ClawDetail clawName={params.name} />
      </div>
    </main>
  );
}
